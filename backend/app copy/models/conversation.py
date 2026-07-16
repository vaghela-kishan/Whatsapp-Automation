"""Conversation model — a thread of messages with a single customer."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.enums import ConversationStatus

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.message import Message


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A support thread. One customer can have many over time."""

    __tablename__ = "conversations"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, native_enum=False, length=20),
        default=ConversationStatus.OPEN,
        nullable=False,
        index=True,
    )
    subject: Mapped[str | None] = mapped_column(String(160), nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    # Denormalised preview for fast conversation lists (no message join needed).
    last_message_preview: Mapped[str | None] = mapped_column(String(280), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Sentiment/priority — angry customers are surfaced & handled first.
    sentiment: Mapped[str] = mapped_column(String(12), default="neutral", nullable=False)
    priority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    customer: Mapped["Customer"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Conversation {self.id} status={self.status}>"
