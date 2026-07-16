"""Health-check endpoints used by humans, load balancers, and orchestrators."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.common import HealthResponse

logger = logging.getLogger("app.health")

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness/readiness probe",
    description="Returns service metadata and verifies database connectivity.",
)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    database_status = "up"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - defensive
        logger.exception("health_check_db_failure")
        database_status = "down"

    return HealthResponse(
        status="ok" if database_status == "up" else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=database_status,
    )
