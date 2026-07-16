"""Meta WhatsApp Cloud API transport.

Ready to switch on for production: set ``WHATSAPP_PROVIDER=meta`` and fill
``WHATSAPP_ACCESS_TOKEN`` / ``WHATSAPP_PHONE_NUMBER_ID`` in the environment.
Uses a short-lived synchronous httpx call — fine for our per-message volume.
"""

from __future__ import annotations

import logging

import httpx

from app.integrations.whatsapp.base import SendResult

logger = logging.getLogger("app.whatsapp.meta")


class MetaWhatsAppProvider:
    name = "meta"

    def __init__(
        self, access_token: str, phone_number_id: str, api_version: str = "v21.0"
    ) -> None:
        if not access_token or not phone_number_id:
            raise ValueError(
                "Meta WhatsApp requires WHATSAPP_ACCESS_TOKEN and "
                "WHATSAPP_PHONE_NUMBER_ID"
            )
        self._token = access_token
        self._url = (
            f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        )

    def send_text(self, *, to: str, text: str) -> SendResult:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        headers = {"Authorization": f"Bearer {self._token}"}
        with httpx.Client(timeout=15) as client:
            resp = client.post(self._url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        external_id = data.get("messages", [{}])[0].get("id", "unknown")
        logger.info("whatsapp_meta_send to=%s wamid=%s", to, external_id)
        return SendResult(external_id=external_id, provider=self.name)
