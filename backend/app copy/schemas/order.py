"""Pydantic contracts for orders."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus


class OrderItem(BaseModel):
    name: str
    qty: int = 1
    price: float = 0.0


class OrderBase(BaseModel):
    order_number: str = Field(examples=["AUR-10432"])
    status: OrderStatus = OrderStatus.CONFIRMED
    items: list[OrderItem] = []
    total: float = 0.0
    currency: str = "INR"
    tracking_number: str | None = None
    carrier: str | None = None
    estimated_delivery: datetime | None = None


class OrderCreate(OrderBase):
    customer_id: uuid.UUID


class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    created_at: datetime
