"""In-memory mock WhatsApp transport.

Records every "sent" message in a bounded ring buffer so the demo dashboard can
show an outbound-message feed, and so tests can assert on what was delivered —
all without any network calls or credentials.
"""

from __future__ import annotations

import itertools
import logging
from collections import deque

from app.integrations.whatsapp.base import SendResult

logger = logging.getLogger("app.whatsapp.mock")

# A process-wide log of simulated deliveries (most recent last).
SENT_LOG: deque[dict] = deque(maxlen=200)
_counter = itertools.count(1)


class MockWhatsAppProvider:
    name = "mock"

    def send_text(self, *, to: str, text: str) -> SendResult:
        external_id = f"mock-wamid-{next(_counter)}"
        entry = {"id": external_id, "to": to, "text": text}
        SENT_LOG.append(entry)
        logger.info("whatsapp_mock_send to=%s text=%r", to, text[:60])
        return SendResult(external_id=external_id, provider=self.name)
