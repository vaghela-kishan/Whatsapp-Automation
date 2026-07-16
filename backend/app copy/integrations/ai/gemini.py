"""Google Gemini AI provider.

The ``google-generativeai`` SDK is imported lazily so the application still
starts (and the mock engine still works) when the package or an API key is
absent. Any runtime failure is surfaced as ``AIProviderError`` and the service
layer degrades gracefully to the mock engine.
"""

from __future__ import annotations

import logging

from app.integrations.ai.base import AIResult

logger = logging.getLogger("app.ai.gemini")


class AIProviderError(RuntimeError):
    """Raised when the Gemini backend cannot produce a reply."""


class GeminiAIProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        *,
        max_output_tokens: int = 500,
        temperature: float = 0.4,
    ) -> None:
        if not api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured")
        try:
            import google.generativeai as genai  # noqa: WPS433 (lazy import)
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise AIProviderError(
                "google-generativeai is not installed; run "
                "`pip install google-generativeai`"
            ) from exc

        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model
        self._generation_config = {
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
        }
        # Customer-support replies are benign; disable the safety filters so
        # ordinary phrases (e.g. "my order is broken") aren't false-flagged.
        # NOTE: must use the typed enums — short string keys are silently
        # ignored by the SDK and lead to spurious "dangerous_content" blocks.
        from google.generativeai.types import HarmBlockThreshold, HarmCategory

        self._safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def generate_reply(self, *, system_prompt: str, user_message: str) -> AIResult:
        try:
            model = self._genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=system_prompt,
                generation_config=self._generation_config,
                safety_settings=self._safety_settings,
            )
            response = model.generate_content(user_message)
            text = self._extract_text(response)
        except Exception as exc:  # pragma: no cover - network/SDK errors
            logger.warning("gemini_generate_failed error=%s", exc)
            raise AIProviderError(str(exc)) from exc

        if not text:
            raise AIProviderError("Gemini returned an empty or blocked response")

        # Heuristic: if the model asked to hand off, mark for escalation.
        escalate = "human" in text.lower() and "connect" in text.lower()
        return AIResult(
            text=text,
            confidence=0.85,
            escalate=escalate,
            model=self._model_name,
        )

    @staticmethod
    def _extract_text(response) -> str:
        """Safely pull text out of a Gemini response (handles blocked/empty)."""
        text = (getattr(response, "text", None) or "").strip()
        if text:
            return text
        # Fall back to scanning candidate parts if ``.text`` was unavailable.
        for candidate in getattr(response, "candidates", []) or []:
            parts = getattr(getattr(candidate, "content", None), "parts", []) or []
            joined = " ".join(getattr(p, "text", "") for p in parts).strip()
            if joined:
                return joined
        return ""
