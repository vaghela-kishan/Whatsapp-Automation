"""Conversation orchestration — the heart of the automation.

``handle_inbound`` implements the full pipeline for one customer message:

    identify customer → open/continue conversation → persist inbound →
    detect intent → resolve an answer (order lookup / FAQ / AI) →
    persist + send outbound → update conversation state.

Deterministic facts (order status, FAQ answers) are used verbatim — they are
authoritative and nicely formatted. Only open-ended turns (greetings, unknown
questions, escalations) are handed to the AI provider for phrasing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.conversation import conversation as conversation_crud
from app.crud.customer import customer as customer_crud
from app.integrations.ai import get_ai_provider
from app.integrations.ai import order_agent
from app.integrations.ai.order_agent import OrderAgentError
from app.integrations.whatsapp import get_whatsapp_provider
from app.models.conversation import Conversation
from app.models.enums import (
    ConversationStatus,
    Intent,
    MessageDirection,
    SenderType,
)
from app.models.message import Message
from app.services import ai_service, faq_service, intent as intent_svc, order_service

logger = logging.getLogger("app.conversation")


@dataclass(slots=True)
class HandledMessage:
    conversation: Conversation
    inbound: Message
    outbound: Message
    intent: Intent
    escalated: bool
    handled_by: str


@dataclass(slots=True)
class Resolution:
    """A routing decision. ``reply_text`` set → send verbatim; ``None`` → ask AI."""

    reply_text: str | None
    escalate: bool = False
    confidence: float = 0.9


def _preview(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _greeting_reply(text: str) -> str:
    """A warm, language-aware greeting — handled without any AI call (0 quota)."""
    from app.core.config import settings

    name = settings.ASSISTANT_NAME
    biz = settings.BUSINESS_NAME
    if intent_svc.looks_non_english(text):
        # Romanized Gujarati/Hindi — understood by Gujarati & Hindi speakers.
        return (
            f"Namaste! 👋 Hu {name}, {biz} no AI assistant. Hu order track karva, "
            "products vishe, delivery, return ke payment na jawab aapva madad kari "
            "shaku — ke tamne human team sathe jodi shaku. Bolo, su madad karu? 😊"
        )
    return (
        f"Hi there! 👋 I'm {name}, the AI assistant at {biz}. I can help you track "
        "an order, answer questions about delivery, returns or payments, or connect "
        "you with our team. What can I help you with? 😊"
    )


def _recent_order_context(db: Session, conversation_id) -> bool:
    """True if the immediately previous customer turn was order-related — so a
    short follow-up ('refund', 'yes', a reason) continues that flow through the
    agent instead of being misread as a greeting/unknown and losing context."""
    last = db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.direction == MessageDirection.INBOUND,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return bool(last and last.intent in (Intent.ORDER_STATUS, Intent.ORDER_QUERY))


def _agent_history(db: Session, conversation_id, limit: int = 8) -> list[dict]:
    """Recent prior turns of the conversation, formatted for the Gemini chat so
    the agent can hold multi-turn context (e.g. confirm before cancelling)."""
    rows = db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).scalars().all()
    history: list[dict] = []
    for m in reversed(rows):
        role = "user" if m.direction == MessageDirection.INBOUND else "model"
        history.append({"role": role, "parts": [m.content]})
    return history


def _order_fallback(db: Session, text: str, wa_id: str) -> str:
    """Deterministic, DB-backed order answer used when the AI agent can't run
    (e.g. quota exhausted) — so order questions still work, just in English."""
    number = intent_svc.extract_order_number(text)
    if number:
        _, reply = order_service.resolve_status(db, number)
        return reply
    lowered = text.lower()
    # Aggregate query (count/list/price/sales) → whole-book answer.
    if intent_svc._is_order_query(lowered):
        return order_service.answer_order_query(db, text)
    # Otherwise treat it as "my orders" — list the caller's own orders.
    customer = customer_crud.get_by_wa_id(db, wa_id)
    return order_service.format_customer_orders(db, customer)


def _resolve(db: Session, detected: Intent, text: str) -> Resolution:
    """Decide how to answer a message based on its detected intent."""
    if detected is Intent.ORDER_QUERY:
        # Aggregate DB-backed answer (list / count / by-price / by-status).
        return Resolution(reply_text=order_service.answer_order_query(db, text), confidence=0.95)

    if detected is Intent.ORDER_STATUS:
        order_number = intent_svc.extract_order_number(text)
        if not order_number:
            # No number quoted — it may be a general order how-to
            # ("how do I track my order?"). Prefer a knowledge-base answer;
            # otherwise ask for the number so we can look it up.
            match = faq_service.find_best_match(db, text)
            if match:
                faq_service.record_hit(db, match.faq)
                return Resolution(reply_text=match.faq.answer, confidence=0.88)
            return Resolution(
                reply_text=(
                    "Happy to check that for you! 📦 Could you share your order "
                    "number? It looks like *AUR-10432* and is in your confirmation "
                    "message."
                ),
                confidence=0.85,
            )
        _, reply_text = order_service.resolve_status(db, order_number)
        return Resolution(reply_text=reply_text, confidence=0.96)

    if detected is Intent.FAQ:
        match = faq_service.find_best_match(db, text)
        if match:
            faq_service.record_hit(db, match.faq)
            return Resolution(reply_text=match.faq.answer, confidence=0.9)
        # A question we have no KB answer for → log it (self-learning) + escalate.
        faq_service.record_unanswered(db, text)
        return Resolution(reply_text=None, escalate=True)

    if detected is Intent.UNKNOWN:
        match = faq_service.find_best_match(db, text)
        if match:
            faq_service.record_hit(db, match.faq)
            return Resolution(reply_text=match.faq.answer, confidence=0.85)
        return Resolution(reply_text=None, escalate=False)

    if detected is Intent.SUPPORT:
        # A support message phrased as a question (e.g. "when will I get my
        # refund?", "how do I return an item?") may be answerable from the KB —
        # answer it instead of escalating a real complaint/request.
        if intent_svc.is_question(text):
            match = faq_service.find_best_match(db, text)
            if match:
                faq_service.record_hit(db, match.faq)
                return Resolution(reply_text=match.faq.answer, confidence=0.85)
        return Resolution(reply_text=None, escalate=True)

    # GREETING and everything else: free-form AI reply.
    return Resolution(reply_text=None, escalate=False)


def handle_inbound(
    db: Session, *, wa_id: str, text: str, name: str | None = None
) -> HandledMessage:
    """Process one inbound WhatsApp message end-to-end."""
    customer = customer_crud.get_or_create(db, wa_id=wa_id, name=name)

    convo = conversation_crud.get_active_for_customer(db, customer.id)
    if convo is None:
        convo = Conversation(customer_id=customer.id, status=ConversationStatus.OPEN)
        db.add(convo)
        db.flush()  # assign id without committing yet

    detected = intent_svc.classify(text)

    inbound = Message(
        conversation_id=convo.id,
        direction=MessageDirection.INBOUND,
        sender=SenderType.CUSTOMER,
        content=text,
        intent=detected,
    )
    db.add(inbound)

    ai_available = get_ai_provider().name != "mock"
    # Are we mid-order-conversation (last turn was order-related)? If so, a short
    # follow-up like "refund", "yes" or a reason must continue via the agent.
    in_order_flow = ai_available and _recent_order_context(db, convo.id)

    reply_text: str | None = None
    confidence = 0.0
    escalated = False

    # --- Greetings: handled deterministically (0 AI calls, any language) ---
    # ...but never treat a mid-flow follow-up as a fresh greeting.
    if detected is Intent.GREETING and not in_order_flow:
        reply_text = _greeting_reply(text)
        confidence = 0.9
        escalated = False

    # --- Agentic order intelligence -------------------------------------
    # Give the AI direct DB access (read + actions) for ANY order-related
    # message — track, details, cancel, return, refund, invoice — in any
    # language. This INCLUDES order-related "support" messages (cancel/return/
    # damaged order) and mid-flow follow-ups, because those are real actions the
    # agent performs with its tools. On quota exhaustion we fall back to a
    # deterministic DB answer.
    elif ai_available and (intent_svc.is_order_related(text) or in_order_flow):
        detected = (
            Intent.ORDER_STATUS
            if intent_svc.extract_order_number(text)
            else Intent.ORDER_QUERY
        )
        inbound.intent = detected
        try:
            history = _agent_history(db, convo.id)
            reply_text = order_agent.run(db, wa_id=wa_id, text=text, history=history)
            confidence = 0.9
        except OrderAgentError:
            # Deterministic DB answer (English) instead of a generic escalation.
            reply_text = _order_fallback(db, text, wa_id)
            confidence = 0.6
        low = (reply_text or "").lower()
        escalated = any(
            p in low
            for p in (
                "human agent", "human team", "our team will", "team will reach",
                "reach out to you", "get back to you", "call you back",
                "contact you", "teammate", "escalat", "connect you",
                "human teammate", "reach out on whatsapp",
            )
        )

    if reply_text is None:
        resolution = _resolve(db, detected, text)
        if resolution.reply_text is not None:
            # Verified fact (order status / FAQ). Relay through the AI only when
            # the message is non-English (lands in their language); English
            # keeps the crisp templates and spends no AI call (saves quota).
            if ai_available and intent_svc.looks_non_english(text):
                ai_result = ai_service.generate(
                    user_message=text, context_answer=resolution.reply_text
                )
                reply_text = ai_result.text
            else:
                reply_text = resolution.reply_text
            confidence = resolution.confidence
            escalated = resolution.escalate
        else:
            # Open-ended turn — free-form AI reply (in any language).
            ai_result = ai_service.generate(user_message=text)
            reply_text = ai_result.text
            confidence = ai_result.confidence
            escalated = resolution.escalate or ai_result.escalate

    outbound = Message(
        conversation_id=convo.id,
        direction=MessageDirection.OUTBOUND,
        sender=SenderType.AI,
        content=reply_text,
        confidence=confidence,
    )
    db.add(outbound)

    # Sentiment/priority — an angry customer is flagged AND routed to a human so
    # a person follows up, and they surface at the top of the agent queue.
    sentiment = intent_svc.detect_sentiment(text)
    if sentiment == "angry":
        convo.sentiment = "angry"
        convo.priority = True
        escalated = True
    elif sentiment == "negative" and convo.sentiment != "angry":
        convo.sentiment = "negative"

    convo.last_message_preview = _preview(reply_text)
    convo.last_message_at = func.now()
    if escalated:
        convo.status = ConversationStatus.NEEDS_HUMAN
    db.add(convo)

    db.commit()
    db.refresh(convo)
    db.refresh(inbound)
    db.refresh(outbound)

    # Deliver the reply over the configured WhatsApp transport.
    try:
        result = get_whatsapp_provider().send_text(to=wa_id, text=reply_text)
        outbound.external_id = result.external_id
        db.commit()
        db.refresh(outbound)
    except Exception as exc:  # delivery failure shouldn't lose the reply record
        logger.warning("whatsapp_send_failed wa_id=%s error=%s", wa_id, exc)

    logger.info(
        "handled_inbound wa_id=%s intent=%s escalated=%s conf=%.2f",
        wa_id,
        detected,
        escalated,
        confidence,
    )

    return HandledMessage(
        conversation=convo,
        inbound=inbound,
        outbound=outbound,
        intent=detected,
        escalated=escalated,
        handled_by="ai",
    )


def post_agent_reply(db: Session, *, convo: Conversation, text: str) -> Message:
    """Record and send a human agent's manual reply into a conversation."""
    message = Message(
        conversation_id=convo.id,
        direction=MessageDirection.OUTBOUND,
        sender=SenderType.AGENT,
        content=text,
    )
    db.add(message)
    convo.last_message_preview = _preview(text)
    convo.last_message_at = func.now()
    db.add(convo)
    db.commit()
    db.refresh(message)

    try:
        result = get_whatsapp_provider().send_text(to=convo.customer.wa_id, text=text)
        message.external_id = result.external_id
        db.commit()
        db.refresh(message)
    except Exception as exc:
        logger.warning("agent_reply_send_failed error=%s", exc)

    return message
