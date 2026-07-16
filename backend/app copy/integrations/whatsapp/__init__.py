"""WhatsApp provider factory."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.integrations.whatsapp.base import SendResult, WhatsAppProvider
from app.integrations.whatsapp.mock import MockWhatsAppProvider

logger = logging.getLogger("app.whatsapp")

_provider: WhatsAppProvider | None = None


def _build_provider() -> WhatsAppProvider:
    if settings.WHATSAPP_PROVIDER == "meta":
        try:
            from app.integrations.whatsapp.meta import MetaWhatsAppProvider

            provider = MetaWhatsAppProvider(
                access_token=settings.WHATSAPP_ACCESS_TOKEN,
                phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
                api_version=settings.WHATSAPP_API_VERSION,
            )
            logger.info("whatsapp_provider_ready provider=meta")
            return provider
        except Exception as exc:
            logger.warning(
                "whatsapp_provider_meta_unavailable falling_back_to=mock reason=%s", exc
            )

    logger.info("whatsapp_provider_ready provider=mock")
    return MockWhatsAppProvider()


def get_whatsapp_provider() -> WhatsAppProvider:
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


__all__ = ["WhatsAppProvider", "SendResult", "get_whatsapp_provider"]
