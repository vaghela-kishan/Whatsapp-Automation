"""FAQ matching.

A small token-overlap scorer ranks knowledge-base entries against a question.
It weights explicit ``keywords`` higher than incidental question-word overlap,
returning the best match only when confidence clears a threshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.faq import faq as faq_crud
from app.models.faq import FAQ

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an the is are do does can i my me you your we our of to for on in at "
    "and or how what when where why it this that with please have any here".split()
)

# Raised so a single incidental word (e.g. "available") no longer matches an
# unrelated FAQ — genuinely new questions fall through to the self-learning log.
MATCH_THRESHOLD = 0.7


@dataclass(slots=True)
class FAQMatch:
    faq: FAQ
    score: float


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


def _score(query_tokens: set[str], entry: FAQ) -> float:
    if not query_tokens:
        return 0.0
    keyword_tokens = _tokens(entry.keywords)
    question_tokens = _tokens(entry.question)

    keyword_hits = len(query_tokens & keyword_tokens)
    question_hits = len(query_tokens & question_tokens)

    # Keyword overlap is worth 2x an incidental question-word overlap.
    weighted = (keyword_hits * 2.0) + question_hits
    denom = len(query_tokens) + 1.0
    return weighted / denom


def find_best_match(db: Session, text: str) -> FAQMatch | None:
    """Return the best-scoring active FAQ, or ``None`` if none clears the bar."""
    query_tokens = _tokens(text)
    best: FAQMatch | None = None
    for entry in faq_crud.list_active(db):
        score = _score(query_tokens, entry)
        if best is None or score > best.score:
            best = FAQMatch(faq=entry, score=score)

    if best and best.score >= MATCH_THRESHOLD:
        return best
    return None


def record_hit(db: Session, entry: FAQ) -> None:
    """Increment an FAQ's served counter (powers the 'top FAQs' widget)."""
    entry.hit_count += 1
    db.commit()


def record_unanswered(db: Session, text: str) -> None:
    """Log a question the knowledge base couldn't answer (self-learning loop).
    De-duplicates by a normalised key and bumps ``ask_count``."""
    from app.models.faq_suggestion import FAQSuggestion

    q = " ".join(text.split()).strip()
    if len(q) < 6 or len(q) > 280:
        return
    normalized = " ".join(w for w in _WORD_RE.findall(q.lower()) if w not in _STOPWORDS)
    if not normalized:
        return
    existing = db.execute(
        select(FAQSuggestion).where(
            FAQSuggestion.normalized == normalized,
            FAQSuggestion.status == "pending",
        )
    ).scalar_one_or_none()
    if existing:
        existing.ask_count += 1
    else:
        db.add(FAQSuggestion(question=q, normalized=normalized, ask_count=1))
    db.commit()
