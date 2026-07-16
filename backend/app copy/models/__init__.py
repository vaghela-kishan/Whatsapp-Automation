"""SQLAlchemy model registry.

Every ORM model must be imported here so that:
  1. Alembic autogenerate can discover it via ``Base.metadata``.
  2. Relationship string references resolve at mapper-configuration time.
  3. ``Base.metadata.create_all`` (used on startup in dev) sees every table.

Keep this file as the single import surface for all models.
"""

from __future__ import annotations

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.enums import (
    ConversationStatus,
    Intent,
    MessageDirection,
    OrderStatus,
    SenderType,
)
from app.models.faq import FAQ
from app.models.faq_suggestion import FAQSuggestion
from app.models.message import Message
from app.models.order import Order
from app.models.order_event import OrderEvent

__all__ = [
    "Customer",
    "Conversation",
    "Message",
    "Order",
    "OrderEvent",
    "FAQ",
    "FAQSuggestion",
    "ConversationStatus",
    "Intent",
    "MessageDirection",
    "OrderStatus",
    "SenderType",
]
