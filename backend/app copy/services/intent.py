"""Lightweight intent detection.

A fast, transparent, dependency-free classifier that decides how to route an
inbound message *before* we spend an AI call, and extracts an order number when
present. Good enough to demo real routing; easy to later swap for an LLM
classifier behind the same ``classify`` function.

Ordering matters: an explicit order number wins, then personal order-tracking
phrasing, then *questions* (which are informational and go to the FAQ matcher),
then complaint/human-handoff statements, then greetings.
"""

from __future__ import annotations

import re

from app.models.enums import Intent

# Order numbers look like AUR-10432 (prefix - digits). Case-insensitive.
ORDER_NUMBER_RE = re.compile(r"\b([A-Z]{2,4}-\d{3,8})\b", re.IGNORECASE)

# Phrases that mean "this is about *my* order" even without a number.
_PERSONAL_ORDER = (
    "where is my", "track my", "where's my", "status of my", "my order",
    "when will my", "when will i get", "has my order", "did my order",
)
# Words that mean a customer wants a human / has a problem (as a statement).
_COMPLAINT = (
    "refund", "cancel", "complaint", "broken", "damaged", "defective",
    "not working", "doesn't work", "wrong item", "wrong product", "missing",
    "return this", "want to return", "return my", "replace",
)
_HUMAN_REQUEST = (
    "speak to", "talk to", "human", "agent", "representative", "need help",
    "customer care", "someone help", "real person",
)
# Aggregate/analytics phrasing about the whole order book (not one order).
# Strong phrases imply an order-book query on their own:
_ORDER_QUERY_STRONG = (
    "total sales", "total revenue", "how many orders", "all orders",
    "list all orders", "order book", "sales figures", "kul order", "ketla order",
    "badha order",
)
# Trigger words that, combined with the word "order", mean an aggregate query:
_ORDER_QUERY_TRIGGERS = (
    "list", "show", "all ", "how many", "how much", "count", "total",
    "number of", "recent", "latest", "above", "below", "over", "under",
    "more than", "less than", "greater", "top", "expensive", "costliest",
    "cheapest", "highest", "biggest", "largest", "pending", "delivered",
    "shipped", "cancelled", "canceled", "returned", "packed", "confirmed",
    "out for delivery", "worth", "sales", "revenue", "which", "what",
)
# Generic order-tracking vocabulary (weaker than a number or personal phrasing).
_ORDER_TERMS = (
    "track", "tracking", "shipped", "dispatch", "courier", "parcel", "package",
)
# Whole-word greeting tokens (matched against message tokens, NOT substrings —
# otherwise "hi" would wrongly match inside "chhiye", "this", etc.).
_GREETING_TOKENS = frozenset(
    "hello helo hey heya namaste namaskar kemcho hola yo vanakkam salaam"
    " morning evening".split()
)
# Multi-word greeting phrases.
_GREETING_PHRASES = (
    "good morning", "good evening", "good afternoon", "kem cho", "kem chho",
    "ram ram", "jai shree", "sat sri akal", "shubh",
)
_QUESTION_STARTS = (
    "what", "how", "when", "where", "which", "can i", "can you", "do you",
    "does", "is there", "are you", "why", "who",
)


def extract_order_number(text: str) -> str | None:
    match = ORDER_NUMBER_RE.search(text)
    return match.group(1).upper() if match else None


def _has(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _is_question(lowered: str) -> bool:
    return "?" in lowered or lowered.startswith(_QUESTION_STARTS)


def _is_greeting(lowered: str) -> bool:
    """A short, pure greeting — matched on whole words/phrases (never as a
    substring, so 'chhiye'/'this' don't count as 'hi')."""
    if any(p in lowered for p in _GREETING_PHRASES):
        return len(lowered.split()) <= 5
    tokens = re.findall(r"[a-z]+", lowered)
    if not tokens or len(tokens) > 4:
        return False
    return any(
        t in _GREETING_TOKENS or re.fullmatch(r"hi+", t) or re.fullmatch(r"hey+", t)
        for t in tokens
    )


def _is_order_query(lowered: str) -> bool:
    """Aggregate question about the whole order book (list/count/price/status)."""
    if _has(lowered, _ORDER_QUERY_STRONG):
        return True
    return "order" in lowered and _has(lowered, _ORDER_QUERY_TRIGGERS)


# Romanized order words across Gujarati/Hindi so order questions route to the
# agentic DB layer even when written in another language.
_ORDER_WORDS = ("order", "orders", "ऑर्डर", "ઓર્ડર", "आर्डर")


def is_order_related(text: str) -> bool:
    """Broad check: is this message about orders (any language)? Used to route
    to the agentic order-database layer."""
    lowered = text.lower()
    if extract_order_number(text) is not None:
        return True
    if _is_order_query(lowered):
        return True
    return any(w in lowered for w in _ORDER_WORDS)


def is_question(text: str) -> bool:
    """Public helper: does this message read like an (informational) question?"""
    return _is_question(text.lower().strip())


# Distinctly Indic romanized (Gujlish/Hinglish) tokens — rare in English. Used
# to decide when to spend an AI call translating a reply into the customer's
# language (English messages keep the crisp templates and save quota).
_ROMANIZED_INDIC = frozenset(
    "chhe che kem cho shu kyare mara maru mane nathi joie joishe karo karvu "
    "kevi kevu aavshe thayu thay kyu kyun kaise kaisa nahi nahin kripya aapka "
    "aapki mujhe kahan batao chahiye kitna kitne kya nu ne mane tamaru tame "
    "hoy jaie madad joiye".split()
)


# Words signalling an upset/angry customer (English + romanized Hindi/Gujarati).
_ANGRY_TERMS = (
    "angry", "furious", "worst", "terrible", "horrible", "pathetic", "useless",
    "disgusting", "cheated", "cheat", "fraud", "scam", "ridiculous", "unacceptable",
    "fed up", "sick of", "never again", "waste", "third class", "bakwas", "bekar",
    "ghatiya", "faltu", "hopeless", "harassment", "complaint", "escalate",
    "consumer court", "legal", "sue",
)
_NEGATIVE_TERMS = (
    "not happy", "disappointed", "unhappy", "frustrated", "upset", "annoyed",
    "poor service", "bad service", "delay", "still waiting", "no response",
    "not working", "damaged", "broken", "wrong", "missing",
)


def detect_sentiment(text: str) -> str:
    """Coarse sentiment: 'angry' | 'negative' | 'neutral'. Deterministic (no AI)
    so it costs nothing and works in every language we romanize."""
    lowered = text.lower()
    if _has(lowered, _ANGRY_TERMS) or text.count("!") >= 3:
        return "angry"
    # Shouting in ALL CAPS (of a reasonably long message) reads as anger.
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 8 and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        return "angry"
    if _has(lowered, _NEGATIVE_TERMS):
        return "negative"
    return "neutral"


def looks_non_english(text: str) -> bool:
    """Heuristic: is the message written in a non-English language/script?

    True for any non-Latin script (Gujarati, Hindi/Devanagari, etc.) or when the
    message contains common romanized Gujlish/Hinglish markers.
    """
    for ch in text:
        code = ord(ch)
        # Devanagari, Bengali, Gurmukhi, Gujarati, Tamil, Telugu, … blocks.
        if 0x0900 <= code <= 0x0D7F or 0x0A00 <= code <= 0x0AFF:
            return True
    tokens = {t for t in re.findall(r"[a-z]+", text.lower())}
    return bool(tokens & _ROMANIZED_INDIC)


def classify(text: str) -> Intent:
    """Return the best-guess :class:`Intent` for a raw message."""
    lowered = text.lower().strip()
    if not lowered:
        return Intent.UNKNOWN

    has_number = extract_order_number(text) is not None
    is_complaint = _has(lowered, _COMPLAINT)

    # 1. An explicit order number is the strongest signal.
    if has_number:
        return Intent.SUPPORT if is_complaint else Intent.ORDER_STATUS

    # 2. Personal order-tracking phrasing ("where is my order") — one order.
    if _has(lowered, _PERSONAL_ORDER):
        return Intent.SUPPORT if is_complaint else Intent.ORDER_STATUS

    # 2b. Aggregate questions about the whole order book ("list all orders",
    #     "orders above 5000", "how many delivered orders", "total sales").
    if _is_order_query(lowered):
        return Intent.ORDER_QUERY

    # 3. Questions are informational — let the FAQ matcher decide.
    #    (A no-match FAQ later escalates to a human.)
    if _is_question(lowered):
        return Intent.FAQ

    # 4. Complaints / explicit human requests phrased as statements.
    if is_complaint or _has(lowered, _HUMAN_REQUEST):
        return Intent.SUPPORT

    # 5. Short pure greetings (whole-word matched).
    if _is_greeting(lowered):
        return Intent.GREETING

    # 6. Order vocabulary without a number/question ("track my order").
    if _has(lowered, _ORDER_TERMS):
        return Intent.ORDER_STATUS

    return Intent.UNKNOWN
