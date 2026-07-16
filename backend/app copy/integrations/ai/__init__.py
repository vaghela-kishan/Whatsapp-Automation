"""AI provider factory.

``get_ai_provider()`` returns the configured engine, transparently falling back
to the mock engine if Gemini is selected but unavailable — so the app never
fails to start over a missing key.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.integrations.ai.base import AIProvider, AIResult
from app.integrations.ai.mock import MockAIProvider

logger = logging.getLogger("app.ai")

_provider: AIProvider | None = None


def _build_provider() -> AIProvider:
    if settings.AI_PROVIDER == "gemini":
        try:
            from app.integrations.ai.gemini import GeminiAIProvider

            provider = GeminiAIProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                temperature=settings.AI_TEMPERATURE,
            )
            logger.info("ai_provider_ready provider=gemini model=%s", settings.GEMINI_MODEL)
            return provider
        except Exception as exc:  # AIProviderError or import error
            logger.warning(
                "ai_provider_gemini_unavailable falling_back_to=mock reason=%s", exc
            )

    logger.info("ai_provider_ready provider=mock")
    return MockAIProvider(
        assistant_name=settings.ASSISTANT_NAME,
        business_name=settings.BUSINESS_NAME,
    )


def get_ai_provider() -> AIProvider:
    """Return the process-wide AI provider singleton (lazily built)."""
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


__all__ = ["AIProvider", "AIResult", "get_ai_provider"]
