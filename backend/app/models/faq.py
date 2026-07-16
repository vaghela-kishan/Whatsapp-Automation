"""FAQ model — a curated question/answer the assistant can quote verbatim."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FAQ(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A knowledge-base entry. ``keywords`` is a comma-separated list used by
    the lightweight matcher to route questions to this answer."""

    __tablename__ = "faqs"

    question: Mapped[str] = mapped_column(String(300), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="General", nullable=False, index=True)
    keywords: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # How many times this answer has been served — powers a "top FAQs" widget.
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<FAQ {self.question[:40]!r}>"
