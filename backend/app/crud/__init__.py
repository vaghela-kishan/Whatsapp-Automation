"""CRUD repository singletons — import as ``from app.crud import customer``."""

from __future__ import annotations

from app.crud.conversation import conversation
from app.crud.customer import customer
from app.crud.faq import faq
from app.crud.order import order

__all__ = ["customer", "conversation", "order", "faq"]
