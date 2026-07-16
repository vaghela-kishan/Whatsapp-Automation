"""Message model — a single WhatsApp message inside a conversation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.enums import Intent, MessageDirection, SenderType

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One message. Inbound messages carry a detected ``intent``; outbound
    AI messages may carry the ``confidence`` the assistant had in its reply."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, native_enum=False, length=12), nullable=False
    )
    sender: Mapped[SenderType] = mapped_column(
        Enum(SenderType, native_enum=False, length=12), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Set on inbound messages after classification; null on outbound.
    intent: Mapped[Intent | None] = mapped_column(
        Enum(Intent, native_enum=False, length=20), nullable=True
    )
    # 0..1 confidence for AI-authored replies (null otherwise).
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Provider-side message id (e.g. WhatsApp wamid) for delivery correlation.
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Message {self.direction}/{self.sender}: {self.content[:30]!r}>"
