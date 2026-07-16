"""FAQSuggestion — a customer question the bot could NOT answer.

When the knowledge base has no good match, the question is recorded here (and
de-duplicated by a normalised key with a running ``ask_count``). An admin later
reviews these, writes an answer, and approves → it becomes a live FAQ. That
closes the loop and makes the assistant smarter over time.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FAQSuggestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "faq_suggestions"

    question: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized: Mapped[str] = mapped_column(String(300), index=True, nullable=False)
    ask_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # pending | approved | dismissed
    status: Mapped[str] = mapped_column(String(12), default="pending", nullable=False, index=True)
    suggested_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<FAQSuggestion {self.question[:40]!r} x{self.ask_count}>"
