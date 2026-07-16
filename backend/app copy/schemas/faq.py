"""Pydantic contracts for FAQ knowledge-base entries."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FAQBase(BaseModel):
    question: str = Field(max_length=300)
    answer: str
    category: str = "General"
    keywords: str = Field(default="", description="Comma-separated match terms")
    is_active: bool = True


class FAQCreate(FAQBase):
    pass


class FAQUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None
    keywords: str | None = None
    is_active: bool | None = None


class FAQRead(FAQBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    hit_count: int
    created_at: datetime
