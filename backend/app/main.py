"""FastAPI application factory.

Importing :mod:`app.main` does **not** create the app — call
:func:`create_app` so tests can pass overrides.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api import register_routes
from app.config import Settings, get_settings
from app.errors import install_exception_handlers
from app.logging import configure_logging, get_logger
from app.middleware import RequestIDMiddleware

_log = get_logger("helios.app")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fully wired FastAPI app."""
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        _log.info("startup", environment=settings.environment, version=settings.app_version)
        # Banned-model guard at startup: refuse to boot if the configured
        # default is on the banned list.
        settings.assert_model_allowed(settings.watsonx_default_model)
        settings.assert_model_allowed(settings.watsonx_chat_model)
        yield
        _log.info("shutdown")

    app = FastAPI(
        title="Helios Backend",
        version=settings.app_version,
        description="AI control plane for z/OS modernization. See docs/API.md.",
        openapi_url="/openapi.json",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    install_exception_handlers(app)
    register_routes(app)
    return app


# Uvicorn entrypoint: `uvicorn app.main:app`.
app = create_app()
