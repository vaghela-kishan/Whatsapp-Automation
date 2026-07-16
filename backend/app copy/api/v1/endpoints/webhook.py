"""WhatsApp Cloud API webhook.

This is the real production entry point for the ``FastAPI → Webhook → AI →
Database → Reply`` flow:

* ``GET /webhook/whatsapp``  — Meta's subscription verification handshake.
* ``POST /webhook/whatsapp`` — inbound message notifications from Meta.

Security: when ``WHATSAPP_APP_SECRET`` is configured, every POST is verified
against the ``X-Hub-Signature-256`` HMAC header so forged calls are rejected.

In demo mode (``WHATSAPP_PROVIDER=mock``) you don't need Meta at all — the Live
Chat UI posts to ``/chat/send`` instead — but this endpoint already speaks the
Cloud API payload shape, so switching to real WhatsApp is purely configuration.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.common import Message
from app.services import conversation_service

logger = logging.getLogger("app.webhook")

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.get("/whatsapp", include_in_schema=True, summary="Meta webhook verification")
def verify_webhook(
    mode: str = Query(alias="hub.mode", default=""),
    token: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    """Echo ``hub.challenge`` back when the verify token matches (Meta handshake)."""
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=status.HTTP_403_FORBIDDEN, content="verification failed")


def _signature_valid(raw_body: bytes, signature_header: str | None) -> bool:
    """Validate Meta's ``X-Hub-Signature-256: sha256=<hmac>`` header."""
    if not settings.WHATSAPP_APP_SECRET:
        return True  # verification disabled (demo mode)
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


@router.post("/whatsapp", response_model=Message, summary="Receive inbound WhatsApp messages")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
) -> Response | Message:
    """Parse a Cloud API notification and run each text message through the pipeline."""
    raw_body = await request.body()

    if not _signature_valid(raw_body, x_hub_signature_256):
        logger.warning("webhook_signature_invalid")
        return Response(status_code=status.HTTP_403_FORBIDDEN, content="invalid signature")

    try:
        body = json.loads(raw_body or b"{}")
    except ValueError:
        logger.warning("webhook_bad_json")
        return Message(message="ignored: invalid json")

    processed = 0
    for wa_id, name, text in _iter_text_messages(body):
        try:
            conversation_service.handle_inbound(db, wa_id=wa_id, text=text, name=name)
            processed += 1
        except Exception:  # never fail the webhook — Meta would retry endlessly
            logger.exception("webhook_handle_failed wa_id=%s", wa_id)

    logger.info("webhook_processed messages=%d", processed)
    # Always 200 quickly so Meta doesn't retry.
    return Message(message=f"processed {processed} message(s)")


def _iter_text_messages(body: dict):
    """Yield ``(wa_id, name, text)`` for every inbound text in a Cloud API payload."""
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {
                c.get("wa_id"): c.get("profile", {}).get("name")
                for c in value.get("contacts", [])
            }
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                wa_id = msg.get("from")
                text = msg.get("text", {}).get("body", "")
                if wa_id and text:
                    yield wa_id, contacts.get(wa_id), text
