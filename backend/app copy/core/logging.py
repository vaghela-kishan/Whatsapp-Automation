"""Centralised logging configuration.

Two output modes selected via ``LOG_JSON``:
  * ``false`` (dev)  -> human-readable console lines with the request id.
  * ``true``  (prod) -> single-line JSON, ready for log shippers/ELK.

Call :func:`configure_logging` once during app startup.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings
from app.core.context import get_request_id


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every record as ``record.request_id``."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure the root logger and align uvicorn's loggers with it."""
    level = settings.LOG_LEVEL.upper()

    # Ensure emoji/non-ASCII in log messages never crash the handler on Windows
    # (cp1252 consoles/files raise UnicodeEncodeError otherwise).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover - stream may not support it
            pass

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if settings.LOG_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root.addHandler(handler)

    # Route uvicorn's own loggers through our handler instead of their defaults.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
