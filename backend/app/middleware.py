"""HTTP middleware: request id and structured access logging.

Every inbound request is assigned a `req:<ulid>` id. The id is bound into the
structlog context for the lifetime of the request, attached to every response
as the `X-Request-ID` header, and surfaced in the response envelope (see
:mod:`app.errors`).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

import ulid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.logging import get_logger

REQUEST_ID_HEADER = "X-Request-ID"
_log = get_logger("helios.http")

# Available to handlers / services without going through Request.state.
_request_id_var: ContextVar[str | None] = ContextVar("helios_request_id", default=None)


def current_request_id() -> str:
    """Return the current request id or a newly minted one if outside a request."""
    rid = _request_id_var.get()
    return rid if rid else f"req:{ulid.new().str}"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign / propagate a request id and bind structlog context."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or f"req:{ulid.new().str}"

        token = _request_id_var.set(request_id)
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            _log.error("request.failed", elapsed_ms=round(elapsed_ms, 2))
            raise
        finally:
            _request_id_var.reset(token)

        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id

        # Skip access log for the noisy probes.
        if request.url.path not in {"/healthz", "/readyz"}:
            _log.info(
                "request.completed",
                status=response.status_code,
                elapsed_ms=round(elapsed_ms, 2),
            )

        clear_contextvars()
        return response
