"""Gemini Vision — assess a customer's product photo for damage.

Used by the photo flow: a customer sends a picture of a damaged item, Gemini
looks at it and returns a structured verdict the service layer acts on (e.g.
auto-approve a return). Falls back gracefully if vision/quota is unavailable.
"""

from __future__ import annotations

import json
import logging
import re

from app.core.config import settings

logger = logging.getLogger("app.ai.vision")


class VisionError(RuntimeError):
    pass


_PROMPT = (
    "You are a returns-inspection assistant for an e-commerce store. Look at "
    "this product photo a customer sent{note}. Decide whether the item shows "
    "VISIBLE damage or a defect (cracked, shattered, broken, deep scratches, "
    "torn, dented, leaking, or clearly the wrong/faulty product). "
    "Respond with ONLY compact JSON, no prose, no code fences:\n"
    '{{"damaged": true or false, "severity": "none|minor|major", '
    '"summary": "one short sentence describing what you see"}}'
)


def _parse(text: str) -> dict:
    text = text.strip()
    # strip code fences if the model added them
    text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise VisionError("no JSON in vision response")
    data = json.loads(match.group(0))
    return {
        "damaged": bool(data.get("damaged")),
        "severity": str(data.get("severity", "none")),
        "summary": str(data.get("summary", "")).strip(),
    }


def analyze_damage(image_bytes: bytes, mime_type: str, note: str = "") -> dict:
    """Return {damaged, severity, summary}. Raises VisionError on failure."""
    if settings.AI_PROVIDER != "gemini" or not settings.GEMINI_API_KEY:
        raise VisionError("gemini not configured")
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmBlockThreshold, HarmCategory
    except ImportError as exc:  # pragma: no cover
        raise VisionError("google-generativeai not installed") from exc

    genai.configure(api_key=settings.GEMINI_API_KEY)
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    prompt = _PROMPT.format(note=f" with the note: '{note}'" if note else "")
    try:
        model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL, safety_settings=safety)
        response = model.generate_content(
            [prompt, {"mime_type": mime_type or "image/jpeg", "data": image_bytes}]
        )
        text = (getattr(response, "text", None) or "").strip()
    except Exception as exc:  # network / quota / SDK
        logger.warning("vision_failed error=%s", exc)
        raise VisionError(str(exc)) from exc

    if not text:
        raise VisionError("empty vision response")
    return _parse(text)
