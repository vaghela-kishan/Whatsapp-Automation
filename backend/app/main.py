"""Application entry point.

Uses the application-factory pattern (``create_app``) so tests can build an
isolated instance and startup ordering stays explicit.

Run locally:  ``uvicorn app.main:app --reload``
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks. On startup, bootstrap the DB and demo data."""
    if settings.SEED_ON_STARTUP:
        # Imported lazily so tests that build their own DB can skip this path.
        from app.db.init_db import init_db

        init_db()

        # Start the proactive automation worker (advances orders + notifies).
        from app.services.automation import start_worker

        start_worker()
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        description="Production-grade AI Customer Support Automation Platform API.",
        lifespan=lifespan,
    )

    # Inner-most first: request context/tracing wraps the app...
    app.add_middleware(RequestContextMiddleware)
    # ...and CORS is added last so it is the OUTER-most middleware and thus
    # applies to every response, including error responses.
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Process-Time-ms"],
        )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
        }

    logging.getLogger("app").info(
        "application_started name=%s version=%s env=%s",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
    return app


app = create_app()
