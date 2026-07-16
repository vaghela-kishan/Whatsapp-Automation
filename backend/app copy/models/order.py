"""Order model — a customer purchase the assistant can look up by number."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.enums import OrderStatus

if TYPE_CHECKING:
    from app.models.customer import Customer


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A purchase. ``items`` is a small JSON list of ``{name, qty, price}``."""

    __tablename__ = "orders"

    # Human-facing identifier the customer quotes over chat, e.g. "AUR-10432".
    order_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=20),
        default=OrderStatus.CONFIRMED,
        nullable=False,
        index=True,
    )
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # --- Money breakdown (order details) ---------------------------------
    subtotal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tax: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shipping_charges: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # final amount
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # --- Payment ---------------------------------------------------------
    payment_method: Mapped[str] = mapped_column(String(20), default="UPI", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(20), default="Paid", nullable=False)

    # --- Invoice ---------------------------------------------------------
    invoice_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- Shipping / delivery --------------------------------------------
    tracking_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # --- Refund ----------------------------------------------------------
    # refund_status: none | initiated | processing | completed
    refund_status: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    refund_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    refund_reference: Mapped[str | None] = mapped_column(String(40), nullable=True)
    refund_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Return / Replacement -------------------------------------------
    return_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    return_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    return_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    replacement_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pickup_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    return_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="orders")

    RETURN_WINDOW_DAYS = 7

    @property
    def final_amount(self) -> float:
        return self.total

    def is_within_return_window(self, now: datetime) -> bool:
        if self.delivered_at is None:
            return False
        delivered = self.delivered_at
        # SQLite may return naive datetimes; normalise so we can subtract.
        if delivered.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        elif delivered.tzinfo is not None and now.tzinfo is None:
            delivered = delivered.replace(tzinfo=None)
        return (now - delivered).days <= self.RETURN_WINDOW_DAYS

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Order {self.order_number} status={self.status}>"
