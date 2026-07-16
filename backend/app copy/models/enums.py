"""Domain enumerations shared across models, schemas, and services.

Values are stored as short lowercase strings in the database so they read well
in raw queries and stay stable if the Python member names are ever renamed.
"""

from __future__ import annotations

from enum import StrEnum


class MessageDirection(StrEnum):
    """Which way a message flows relative to our platform."""

    INBOUND = "inbound"  # customer -> us
    OUTBOUND = "outbound"  # us -> customer


class SenderType(StrEnum):
    """Who authored a message."""

    CUSTOMER = "customer"
    AI = "ai"
    AGENT = "agent"  # a human support agent (manual reply)
    SYSTEM = "system"


class ConversationStatus(StrEnum):
    """Lifecycle of a support conversation."""

    OPEN = "open"  # AI is handling it
    NEEDS_HUMAN = "needs_human"  # escalated, waiting on an agent
    RESOLVED = "resolved"


class Intent(StrEnum):
    """Coarse classification of what a customer message is asking for."""

    ORDER_STATUS = "order_status"  # about ONE order (by number)
    ORDER_QUERY = "order_query"  # aggregate: list/count/by-price/by-status
    FAQ = "faq"
    SUPPORT = "support"  # general / needs human
    GREETING = "greeting"
    UNKNOWN = "unknown"


class OrderStatus(StrEnum):
    """Fulfilment stage of a customer order."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PACKED = "packed"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
