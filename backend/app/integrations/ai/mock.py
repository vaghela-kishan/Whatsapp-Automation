"""Mock AI provider.

A deterministic, dependency-free reply engine so the whole platform runs and
demos convincingly without any API key. It is intentionally simple: the real
intelligence (order lookups, FAQ matching) happens in the service layer and is
handed to this engine as context inside the system prompt.
"""

from __future__ import annotations

import re

from app.integrations.ai.base import AIProvider, AIResult

# Small, friendly canned responses keyed by keyword. The service layer usually
# supplies concrete facts (order status, FAQ answer) so these are only the
# fallback voice when no structured answer is available.
_GREETING_RE = re.compile(r"\b(hi|hello|hey|namaste|hola|good\s*(morning|evening))\b", re.I)
_THANKS_RE = re.compile(r"\b(thanks|thank you|thankyou|shukriya|appreciate)\b", re.I)


class MockAIProvider:
    name = "mock"

    def __init__(self, assistant_name: str = "Ava", business_name: str = "our store") -> None:
        self.assistant_name = assistant_name
        self.business_name = business_name

    def generate_reply(self, *, system_prompt: str, user_message: str) -> AIResult:
        text = user_message.strip()

        # If the service layer injected a resolved answer, echo it warmly.
        answer = _extract_context_answer(system_prompt)
        if answer:
            return AIResult(text=answer, confidence=0.92, model=self.name)

        if _GREETING_RE.search(text):
            return AIResult(
                text=(
                    f"Hi there! 👋 I'm {self.assistant_name}, the assistant at "
                    f"{self.business_name}. I can help you track an order, answer "
                    "common questions, or connect you with our team. What do you need?"
                ),
                confidence=0.9,
                model=self.name,
            )

        if _THANKS_RE.search(text):
            return AIResult(
                text="You're very welcome! 😊 Is there anything else I can help with?",
                confidence=0.9,
                model=self.name,
            )

        # Unknown → be honest and arrange a human callback (no live agent).
        return AIResult(
            text=(
                "Thanks for reaching out! 🙏 I've noted this for our support team — "
                "a human agent will personally get back to you on WhatsApp shortly. "
                "You don't need to wait here. Meanwhile, if it's about an order, "
                "share your order number (like AUR-10432) and I can check it "
                "instantly."
            ),
            confidence=0.4,
            escalate=True,
            model=self.name,
        )


def _extract_context_answer(system_prompt: str) -> str | None:
    """Pull a service-provided answer out of the prompt, if present.

    The service layer marks resolved facts with an ``ANSWER:`` line so the mock
    engine can voice them without needing an LLM.
    """
    for line in system_prompt.splitlines():
        if line.startswith("ANSWER:"):
            return line[len("ANSWER:"):].strip()
    return None
