"""Pydantic contracts for conversations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ConversationStatus
from app.schemas.customer import CustomerRead
from app.schemas.message import MessageRead


class ConversationSummary(BaseModel):
    """Lightweight row for the conversation list (no messages loaded)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ConversationStatus
    subject: str | None = None
    last_message_at: datetime
    last_message_preview: str | None = None
    unread_count: int
    sentiment: str = "neutral"
    priority: bool = False
    customer: CustomerRead


class ConversationDetail(ConversationSummary):
    """A conversation with its full message thread."""

    messages: list[MessageRead] = []


class ConversationStatusUpdate(BaseModel):
    status: ConversationStatus


class AgentReply(BaseModel):
    """A human agent's manual reply into a conversation."""

    content: str
