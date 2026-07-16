"""AI orchestration — prompt construction and provider invocation.

Builds the assistant's persona/system prompt (optionally seeded with a
service-resolved fact such as an order status or FAQ answer) and delegates
generation to the configured :class:`AIProvider`.

The assistant is multilingual: it always replies in the *same language and
script* the customer used (Gujarati, Hindi, Hinglish, English, …). Verified
facts are passed through as authoritative context so the AI can relay them
naturally in that language without changing any numbers, IDs or dates.

If the provider errors, generation degrades gracefully — to the verified answer
verbatim when we have one, otherwise to the mock engine — so a reply always
goes out.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.integrations.ai import get_ai_provider
from app.integrations.ai.base import AIResult
from app.integrations.ai.mock import MockAIProvider

logger = logging.getLogger("app.ai.service")

_LANGUAGE_RULE = (
    "IMPORTANT: Reply in the SAME language and script the customer used. "
    "If they write in Gujarati, reply in Gujarati; Hindi → Hindi; "
    "romanized Hinglish/Gujlish → the same romanized style; English → English. "
    "Mirror the customer naturally — never switch to English on your own."
)


def _system_prompt(context_answer: str | None) -> str:
    """Compose the assistant persona, language rule, and any resolved answer."""
    base = (
        f"You are {settings.ASSISTANT_NAME}, the friendly WhatsApp support "
        f"assistant for {settings.BUSINESS_NAME} ({settings.BUSINESS_TAGLINE}). "
        f"Support hours are {settings.SUPPORT_HOURS}. "
        "Keep replies warm, concise and helpful for WhatsApp — short paragraphs, "
        "a little emoji, never robotic. If you cannot help, do NOT pretend to "
        "connect them to a live agent — instead tell the customer that our team "
        "will personally reach out to them on WhatsApp shortly (within a few "
        "working hours) and that they don't need to wait here.\n\n" + _LANGUAGE_RULE
    )
    if context_answer:
        # The AI relays these verified facts in the customer's language. The
        # mock engine reads the same block verbatim (see MockAIProvider).
        base += (
            "\n\nAnswer the customer using ONLY the verified information below. "
            "Keep every order number, tracking ID, date and amount EXACTLY as "
            "given — never invent or change a fact. Convey it naturally in the "
            "customer's language, preserving the friendly tone and emoji.\n"
            f"ANSWER: {context_answer}"
        )
    return base


def generate(*, user_message: str, context_answer: str | None = None) -> AIResult:
    """Generate a reply, degrading gracefully on provider failure."""
    provider = get_ai_provider()
    system_prompt = _system_prompt(context_answer)
    try:
        return provider.generate_reply(
            system_prompt=system_prompt, user_message=user_message
        )
    except Exception as exc:  # provider raised (e.g. Gemini network/quota error)
        logger.warning("ai_generate_failed provider=%s error=%s", provider.name, exc)
        if context_answer:
            # Safest fallback: send the verified answer verbatim (accurate, even
            # if not translated) rather than risk a wrong/empty reply.
            return AIResult(text=context_answer, confidence=0.85, model="fallback")
        fallback = MockAIProvider(
            assistant_name=settings.ASSISTANT_NAME,
            business_name=settings.BUSINESS_NAME,
        )
        return fallback.generate_reply(
            system_prompt=system_prompt, user_message=user_message
        )
