"""Dashboard analytics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.stats import DashboardStats
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardStats, summary="Dashboard metrics")
def dashboard(db: Session = Depends(get_db)) -> DashboardStats:
    return stats_service.build_dashboard(db)
