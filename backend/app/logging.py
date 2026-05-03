"""Structured logging via structlog.

Every log entry carries a `request_id` (when inside a request scope) and an
`event` label. JSON output in production, console output in development.

`configure_logging()` is idempotent and called once from :func:`app.main.create_app`.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    """Wire structlog to stdlib logging at the configured level + format."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    processors: list[Any] = [
        merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Quiet noisy libraries.
    for name in ("uvicorn.access", "httpcore", "httpx"):
        logging.getLogger(name).setLevel(max(level, logging.WARNING))


def get_logger(name: str = "helios") -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to *name*."""
    return structlog.get_logger(name)
