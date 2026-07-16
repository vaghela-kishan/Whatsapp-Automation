"""WhatsApp transport interface.

The platform sends outbound replies through a ``WhatsAppProvider``. In demo mode
this is an in-memory mock; in production it is the Meta Cloud API. The service
layer never imports a concrete provider directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class SendResult:
    external_id: str  # provider message id (wamid or mock id)
    provider: str


@runtime_checkable
class WhatsAppProvider(Protocol):
    name: str

    def send_text(self, *, to: str, text: str) -> SendResult:
        """Deliver a plain-text message to the ``to`` phone number."""
        ...
