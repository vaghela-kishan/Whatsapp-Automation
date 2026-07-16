"""Contracts for the inbound-message / simulator flow."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import Intent
from app.schemas.message import MessageRead


class InboundMessage(BaseModel):
    """A customer message arriving from WhatsApp (or the demo simulator)."""

    wa_id: str = Field(examples=["919876543210"], description="Customer phone id")
    name: str | None = Field(default=None, examples=["Priya"])
    text: str = Field(examples=["Where is my order AUR-10432?"])


class ReplyResult(BaseModel):
    """The outcome of processing one inbound message."""

    conversation_id: str
    intent: Intent
    inbound: MessageRead
    reply: MessageRead
    handled_by: str = Field(examples=["ai"], description="ai | agent | none")
    escalated: bool = False
