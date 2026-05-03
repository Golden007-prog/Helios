"""FastAPI dependency providers.

Single source for every injected service. Singletons are created lazily; tests
override via ``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header

from app.config import Settings, get_settings
from app.errors import ErrorCode, HeliosError
from app.jobs.runner import JobRunner, get_job_runner
from app.models.user import AuthenticatedUser
from app.services.audit_writer import AuditWriter
from app.services.auth import decode_token
from app.services.cloudant import CloudantClient
from app.services.watsonx import WatsonxClient

# --- Long-lived singletons ----------------------------------------------------

@lru_cache(maxsize=1)
def _cloudant_singleton() -> CloudantClient:
    return CloudantClient(get_settings())


@lru_cache(maxsize=1)
def _watsonx_singleton() -> WatsonxClient:
    return WatsonxClient(get_settings())


@lru_cache(maxsize=1)
def _audit_singleton() -> AuditWriter:
    return AuditWriter(_cloudant_singleton(), get_settings())


def reset_dependency_cache() -> None:
    """Tests use this to drop singletons between cases."""
    _cloudant_singleton.cache_clear()
    _watsonx_singleton.cache_clear()
    _audit_singleton.cache_clear()


# --- Provider functions (FastAPI Depends targets) -----------------------------

def get_settings_dep() -> Settings:
    return get_settings()


def get_cloudant() -> CloudantClient:
    return _cloudant_singleton()


def get_watsonx() -> WatsonxClient:
    return _watsonx_singleton()


def get_audit_writer() -> AuditWriter:
    return _audit_singleton()


def get_job_runner_dep() -> JobRunner:
    return get_job_runner()


# --- Auth ---------------------------------------------------------------------

def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    settings: Settings = Depends(get_settings_dep),
) -> AuthenticatedUser:
    """Extract and validate the bearer JWT.

    Raises :class:`HeliosError` with ``UNAUTHORIZED`` for missing/invalid
    tokens. Routes that don't need auth simply don't depend on this.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HeliosError(ErrorCode.UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return decode_token(token, settings)
    except Exception as exc:  # JWTError, ExpiredSignatureError, etc.
        raise HeliosError(ErrorCode.UNAUTHORIZED, f"Invalid token: {exc}") from exc


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
