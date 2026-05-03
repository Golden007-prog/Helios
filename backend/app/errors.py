"""Error envelope, error code catalog, and FastAPI exception handlers.

The catalogue mirrors `docs/API.md § Errors`. Every error response returned by
the backend has the shape:

    { "ok": false,
      "error": { "code": "...", "message": "...", "details": {...} },
      "request_id": "req:..." }
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.logging import get_logger
from app.middleware import current_request_id

_log = get_logger("helios.errors")


class ErrorCode(str, Enum):
    """Canonical error codes — see docs/API.md § Errors."""

    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    REGION_NOT_FOUND = "REGION_NOT_FOUND"
    JCL_NOT_FOUND = "JCL_NOT_FOUND"
    RULE_NOT_FOUND = "RULE_NOT_FOUND"
    RUNBOOK_NOT_FOUND = "RUNBOOK_NOT_FOUND"
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SELF_REVIEW_FORBIDDEN = "SELF_REVIEW_FORBIDDEN"
    STATE_TRANSITION_INVALID = "STATE_TRANSITION_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    WATSONX_UPSTREAM = "WATSONX_UPSTREAM"
    CLOUDANT_UPSTREAM = "CLOUDANT_UPSTREAM"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    INTERNAL = "INTERNAL"


# Default HTTP status for each error code.
_HTTP_FOR_CODE: dict[ErrorCode, int] = {
    ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.REGION_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.JCL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.RULE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.RUNBOOK_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.EVENT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.INVALID_PAYLOAD: 422,  # UNPROCESSABLE_ENTITY (renamed in starlette ≥0.45)
    ErrorCode.REVIEW_REQUIRED: status.HTTP_409_CONFLICT,
    ErrorCode.SELF_REVIEW_FORBIDDEN: status.HTTP_409_CONFLICT,
    ErrorCode.STATE_TRANSITION_INVALID: status.HTTP_409_CONFLICT,
    ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.WATSONX_UPSTREAM: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.CLOUDANT_UPSTREAM: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.NOT_IMPLEMENTED: status.HTTP_501_NOT_IMPLEMENTED,
    ErrorCode.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def http_status_for(code: ErrorCode) -> int:
    return _HTTP_FOR_CODE.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """The body of every non-2xx response."""

    model_config = ConfigDict(extra="forbid")
    ok: bool = Field(default=False)
    error: ErrorBody
    request_id: str


class HeliosError(Exception):
    """Application-layer exception — handlers convert it to an :class:`ErrorEnvelope`."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status or http_status_for(code)


class BobStubError(HeliosError):
    """Marker exception raised by Bob-reserved code paths.

    Returns 501 with `BOB: <message>` so contract tests can locate every stub
    without grepping the source tree.
    """

    def __init__(self, message: str, *, feature: str, spec_doc: str | None = None) -> None:
        super().__init__(
            code=ErrorCode.NOT_IMPLEMENTED,
            message=f"BOB: {message}",
            details={
                "feature": feature,
                "spec": spec_doc,
                "reserved_for": "Bob (audit-trail-bearing AI)",
            },
        )
        self.feature = feature
        self.spec_doc = spec_doc


def _envelope(
    code: ErrorCode, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code.value, "message": message, "details": details or {}},
        "request_id": current_request_id(),
    }


def install_exception_handlers(app: FastAPI) -> None:
    """Register handlers that convert exceptions to the canonical envelope."""

    @app.exception_handler(HeliosError)
    async def _helios_error(_: Request, exc: HeliosError) -> JSONResponse:
        if exc.http_status >= 500 and not isinstance(exc, BobStubError):
            _log.error("helios.error", code=exc.code.value, message=exc.message)
        return JSONResponse(
            status_code=exc.http_status,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Map common HTTP statuses back to the catalogue.
        code = {
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.EVENT_NOT_FOUND,  # generic fallback
            429: ErrorCode.RATE_LIMITED,
            501: ErrorCode.NOT_IMPLEMENTED,
        }.get(exc.status_code, ErrorCode.INTERNAL)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail) if exc.detail else code.value),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(
                ErrorCode.INVALID_PAYLOAD,
                "Request body failed schema validation",
                {"errors": exc.errors()},
            ),
        )

    @app.exception_handler(NotImplementedError)
    async def _not_implemented(_: Request, exc: NotImplementedError) -> JSONResponse:
        # NotImplementedError without an explicit BobStubError still surfaces as a stub.
        msg = str(exc) or "Reserved for Bob"
        if not msg.startswith("BOB:"):
            msg = f"BOB: {msg}"
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=_envelope(ErrorCode.NOT_IMPLEMENTED, msg, {"reserved_for": "Bob"}),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        _log.exception("unhandled", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(ErrorCode.INTERNAL, "Unhandled server error"),
        )
