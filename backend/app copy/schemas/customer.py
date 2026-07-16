"""Pydantic contracts for customers."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    wa_id: str = Field(examples=["919876543210"], description="WhatsApp phone id")
    name: str = Field(default="WhatsApp User", max_length=120)
    email: EmailStr | None = None
    avatar_url: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
