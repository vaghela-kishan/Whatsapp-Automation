"""Proactive automation controls (demo trigger)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.services import automation

router = APIRouter(prefix="/automation", tags=["Automation"])


@router.get("/status", summary="Proactive automation config")
def status() -> dict:
    return {
        "enabled": settings.AUTOMATION_ENABLED,
        "interval_seconds": settings.AUTOMATION_INTERVAL_SECONDS,
        "batch": settings.AUTOMATION_BATCH,
    }


@router.post("/run", summary="Advance orders now (manual tick)")
def run_now(
    count: int = Query(default=4, ge=1, le=20), db: Session = Depends(get_db)
) -> dict:
    """Immediately advance a few in-progress orders and notify customers —
    so you can watch the automation work without waiting for the timer."""
    changed = automation.advance_orders(db, limit=count)
    return {"advanced": changed}
