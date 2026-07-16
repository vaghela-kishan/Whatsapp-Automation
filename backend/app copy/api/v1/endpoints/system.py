"""System/branding info for the frontend (business name, provider modes)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.config import settings
from app.integrations.ai import get_ai_provider
from app.integrations.whatsapp import get_whatsapp_provider
from app.integrations.whatsapp.mock import SENT_LOG
from app.services import ai_service

router = APIRouter(prefix="/system", tags=["System"])


class SystemInfo(BaseModel):
    business_name: str
    business_tagline: str
    assistant_name: str
    support_hours: str
    ai_provider: str
    whatsapp_provider: str
    environment: str
    version: str


@router.get("/info", response_model=SystemInfo, summary="Branding & provider status")
def system_info() -> SystemInfo:
    return SystemInfo(
        business_name=settings.BUSINESS_NAME,
        business_tagline=settings.BUSINESS_TAGLINE,
        assistant_name=settings.ASSISTANT_NAME,
        support_hours=settings.SUPPORT_HOURS,
        ai_provider=get_ai_provider().name,
        whatsapp_provider=get_whatsapp_provider().name,
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )


@router.get("/outbox", summary="Recent simulated WhatsApp deliveries (mock mode)")
def outbox() -> list[dict]:
    """The last messages the mock transport 'delivered' (newest last)."""
    return list(SENT_LOG)


class AITestResult(BaseModel):
    provider: str
    ok: bool
    reply: str
    confidence: float


@router.get("/ai-test", response_model=AITestResult, summary="Verify the live AI works")
def ai_test(
    q: str = Query(default="Hi, are you working?", description="Prompt to send the AI"),
) -> AITestResult:
    """Send a prompt straight to the configured AI engine.

    Use this after setting ``AI_PROVIDER=gemini`` + ``GEMINI_API_KEY`` to confirm
    your key works — a real Gemini reply here means the live AI is wired up.
    """
    result = ai_service.generate(user_message=q)
    return AITestResult(
        provider=get_ai_provider().name,
        ok=bool(result.text),
        reply=result.text,
        confidence=result.confidence,
    )
