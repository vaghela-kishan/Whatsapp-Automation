"""Aggregates all v1 endpoint routers under a single ``api_router``.

Each new module registers its router here, keeping ``main.py`` free of
endpoint-wiring details.

Auth model:
* PUBLIC  — health, system info, auth, and the customer-facing message
  pipeline (``chat`` simulator + Meta ``webhook``). These carry no admin data.
* PROTECTED — every admin/data router below requires a valid admin JWT
  (``Depends(get_current_admin)``), so the dashboard's data is never exposed
  without signing in.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin
from app.api.v1.endpoints import (
    auth,
    automation,
    chat,
    conversations,
    customers,
    faqs,
    health,
    orders,
    stats,
    system,
    webhook,
)

api_router = APIRouter()

# --- Public routers ---------------------------------------------------------
api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(webhook.router)

# --- Protected routers (admin JWT required) ---------------------------------
_admin = [Depends(get_current_admin)]
api_router.include_router(conversations.router, dependencies=_admin)
api_router.include_router(orders.router, dependencies=_admin)
api_router.include_router(faqs.router, dependencies=_admin)
api_router.include_router(customers.router, dependencies=_admin)
api_router.include_router(stats.router, dependencies=_admin)
api_router.include_router(automation.router, dependencies=_admin)
