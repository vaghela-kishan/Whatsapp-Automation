"""The simulator / inbound-message endpoint.

``POST /chat/send`` is what the demo Live Chat UI calls: it accepts a customer
message and returns the full result (detected intent, the stored inbound and
outbound messages, and whether it was escalated). It exercises the exact same
pipeline a real WhatsApp webhook would.

``POST /chat/photo`` accepts a product image: Gemini Vision inspects it for
damage and, if found on a returnable order, auto-creates the return.
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud.customer import customer as customer_crud
from app.crud.order import order as order_crud
from app.integrations.ai import vision
from app.integrations.whatsapp import get_whatsapp_provider
from app.models.conversation import Conversation
from app.models.enums import (
    ConversationStatus,
    Intent,
    MessageDirection,
    OrderStatus,
    SenderType,
)
from app.models.message import Message
from app.schemas.chat import InboundMessage, ReplyResult
from app.schemas.message import MessageRead
from app.services import conversation_service, intent as intent_svc, order_service

logger = logging.getLogger("app.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/send",
    response_model=ReplyResult,
    status_code=status.HTTP_201_CREATED,
    summary="Send a customer message and get the AI reply",
)
def send_message(payload: InboundMessage, db: Session = Depends(get_db)) -> ReplyResult:
    handled = conversation_service.handle_inbound(
        db, wa_id=payload.wa_id, text=payload.text, name=payload.name
    )
    return ReplyResult(
        conversation_id=str(handled.conversation.id),
        intent=handled.intent,
        inbound=MessageRead.model_validate(handled.inbound),
        reply=MessageRead.model_validate(handled.outbound),
        handled_by=handled.handled_by,
        escalated=handled.escalated,
    )


class PhotoMessage(BaseModel):
    wa_id: str
    name: str | None = None
    text: str = ""
    image_base64: str = Field(description="Base64 (may include a data: URL prefix)")
    mime_type: str = "image/jpeg"


@router.post(
    "/photo",
    response_model=ReplyResult,
    status_code=status.HTTP_201_CREATED,
    summary="Send a product photo — Vision AI inspects it for damage",
)
def send_photo(payload: PhotoMessage, db: Session = Depends(get_db)) -> ReplyResult:
    customer = customer_crud.get_or_create(db, wa_id=payload.wa_id, name=payload.name)
    convo = conversation_service.conversation_crud.get_active_for_customer(db, customer.id)
    if convo is None:
        convo = Conversation(customer_id=customer.id, status=ConversationStatus.OPEN)
        db.add(convo)
        db.flush()

    caption = payload.text.strip() or "[sent a product photo]"
    inbound = Message(
        conversation_id=convo.id,
        direction=MessageDirection.INBOUND,
        sender=SenderType.CUSTOMER,
        content=f"📷 {caption}",
        intent=Intent.SUPPORT,
    )
    db.add(inbound)

    # Decode the image (strip any data: URL prefix).
    raw = payload.image_base64.split(",", 1)[-1]
    try:
        image_bytes = base64.b64decode(raw)
    except Exception:
        image_bytes = b""

    reply_text, escalated, confidence = _handle_photo(db, customer, convo, payload.text, image_bytes, payload.mime_type)

    outbound = Message(
        conversation_id=convo.id,
        direction=MessageDirection.OUTBOUND,
        sender=SenderType.AI,
        content=reply_text,
        confidence=confidence,
    )
    db.add(outbound)
    convo.last_message_preview = conversation_service._preview(reply_text)
    convo.last_message_at = conversation_service.func.now()
    if escalated:
        convo.status = ConversationStatus.NEEDS_HUMAN
    db.commit()
    db.refresh(convo)
    db.refresh(inbound)
    db.refresh(outbound)

    try:
        get_whatsapp_provider().send_text(to=customer.wa_id, text=reply_text)
    except Exception:  # pragma: no cover
        pass

    return ReplyResult(
        conversation_id=str(convo.id),
        intent=Intent.SUPPORT,
        inbound=MessageRead.model_validate(inbound),
        reply=MessageRead.model_validate(outbound),
        handled_by="ai",
        escalated=escalated,
    )


def _order_from_conversation(db, convo, customer) -> str | None:
    """Find the most recent order number the customer mentioned in this chat."""
    from sqlalchemy import select

    rows = db.execute(
        select(Message)
        .where(Message.conversation_id == convo.id)
        .order_by(Message.created_at.desc())
        .limit(12)
    ).scalars().all()
    for m in rows:
        num = intent_svc.extract_order_number(m.content or "")
        if num:
            return num
    return None


def _handle_photo(db, customer, convo, note, image_bytes, mime) -> tuple[str, bool, float]:
    if not image_bytes:
        return ("I couldn't read that image — could you resend it? 📷", False, 0.4)
    try:
        verdict = vision.analyze_damage(image_bytes, mime, note)
    except vision.VisionError as exc:
        logger.warning("photo_vision_failed err=%s", exc)
        return (
            "Thanks for the photo! 📷 I'm having trouble inspecting it automatically "
            "right now — our team will review it and get back to you shortly. You "
            "don't need to wait here. 🙏",
            True,
            0.4,
        )

    if not verdict["damaged"]:
        return (
            "Thanks for the photo! 🔍 I looked closely but couldn't clearly see any "
            "damage. Could you take a brighter, closer shot of the issue, or describe "
            "what's wrong? I'm here to help. 😊",
            False,
            0.6,
        )

    # Damage confirmed — find the order to return (caption → recent chat → latest).
    number = intent_svc.extract_order_number(note or "") or _order_from_conversation(db, convo, customer)
    order = order_crud.get_by_number(db, number) if number else None
    if order is not None and order.customer_id != customer.id:
        order = None  # never touch someone else's order
    if order is None:
        order = order_service.latest_returnable_order(db, customer)

    seen = verdict["summary"] or "damage on the product"
    if order is None:
        return (
            f"Oh no — I can see the {verdict['severity']} damage ({seen}). 😟 I'm "
            "sorry about that! Please share the *order number* (like AUR-10432) and "
            "I'll arrange a return and refund right away.",
            False,
            0.8,
        )
    if order.status != OrderStatus.DELIVERED or order.return_id or not order.return_eligible:
        return (
            f"I can see the {verdict['severity']} damage ({seen}). 😟 I've logged this "
            f"for *{order.order_number}* and our team will reach out to you on "
            "WhatsApp shortly to sort out a resolution. You don't need to wait here. 🙏",
            True,
            0.6,
        )

    result = order_service.create_return(db, order, reason="Damaged Product (photo verified)", resolution="refund")
    return (
        f"I'm so sorry — I can clearly see the {verdict['severity']} damage ({seen}). 😟\n\n"
        f"✅ I've *verified it from your photo* and approved a return for "
        f"*{order.order_number}*:\n"
        f"• Return ID: {result['return_id']}\n"
        f"• Pickup: {result['pickup_date']}\n"
        f"• Refund of ₹{result['refund_amount']:,.0f} *initiated* to your "
        f"{order.payment_method} (Ref: {result['refund_reference']}) — it'll reflect "
        "in 5-7 business days.\n\nKeep the item in its packaging for pickup. 📦",
        False,
        0.95,
    )
