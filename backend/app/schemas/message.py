"""Pydantic contracts for messages."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Intent, MessageDirection, SenderType


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    direction: MessageDirection
    sender: SenderType
    content: str
    intent: Intent | None = None
    confidence: float | None = None
    created_at: datetime
