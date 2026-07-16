"""Customer model — a person who contacts us over WhatsApp."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.order import Order


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A WhatsApp contact, keyed by their phone number (``wa_id``)."""

    __tablename__ = "customers"

    # WhatsApp identifier == the customer's phone number in E.164-ish form.
    wa_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="WhatsApp User")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Customer {self.name} ({self.wa_id})>"
