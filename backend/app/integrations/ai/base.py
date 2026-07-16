"""AI provider interface.

Every reply engine (Gemini, mock, or a future one) implements ``AIProvider``.
The service layer depends only on this protocol, so swapping engines is a
config change — never a code change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class AIResult:
    """A generated reply plus metadata the platform records and displays."""

    text: str
    confidence: float = 0.7  # 0..1, how sure the engine is about this reply
    escalate: bool = False  # engine thinks a human should take over
    model: str = "unknown"


@runtime_checkable
class AIProvider(Protocol):
    name: str

    def generate_reply(self, *, system_prompt: str, user_message: str) -> AIResult:
        """Produce a support reply to ``user_message`` under ``system_prompt``."""
        ...
