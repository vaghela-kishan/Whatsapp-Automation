"""OrderEvent — an audit-trail record of every action taken on an order.

Each cancellation, return, replacement or refund the assistant performs is
written here so there is a permanent, queryable history of *what happened, to
which order, why, and when*.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID


class OrderEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One audit entry. ``event_type`` is a stable slug the UI can group on."""

    __tablename__ = "order_events"

    order_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Denormalised for fast activity feeds without a join.
    order_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # order_cancelled | return_requested | replacement_requested |
    # refund_initiated | refund_completed
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    actor: Mapped[str] = mapped_column(String(20), default="ai", nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<OrderEvent {self.event_type} {self.order_number}>"
