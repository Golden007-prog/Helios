"""Liveness, readiness, version probes.

Per docs/API.md §1: `/healthz` is liveness; `/readyz` checks Cloudant +
watsonx reachability and returns 503 with `failed_dependencies[]` if either
is down. `/version` is operator-facing build metadata (not in API.md but
useful for "what's actually deployed?").
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.dependencies import get_cloudant, get_watsonx
from app.envelope import Envelope, ok
from app.errors import ErrorCode
from app.middleware import current_request_id
from app.services.cloudant import CloudantClient
from app.services.watsonx import WatsonxClient
from app.version import build_info

router = APIRouter(tags=["health"])


class HealthPayload(BaseModel):
    status: str = Field(default="ok")


class ReadinessDependency(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class ReadinessPayload(BaseModel):
    status: str
    dependencies: list[ReadinessDependency]
    failed_dependencies: list[str] = Field(default_factory=list)


class VersionPayload(BaseModel):
    version: str
    git_sha: str
    build_time: str
    image_tag: str


@router.get("/healthz", response_model=Envelope[HealthPayload])
async def healthz() -> Envelope[HealthPayload]:
    return ok(HealthPayload())


@router.get("/readyz", response_model=Envelope[ReadinessPayload])
async def readyz(
    cloudant: CloudantClient = Depends(get_cloudant),
    watsonx: WatsonxClient = Depends(get_watsonx),
) -> JSONResponse | Envelope[ReadinessPayload]:
    deps: list[ReadinessDependency] = []

    cloudant_ok, cloudant_detail = await cloudant.ping()
    deps.append(ReadinessDependency(name="cloudant", ok=cloudant_ok, detail=cloudant_detail))

    watsonx_ok, watsonx_detail = await watsonx.ping()
    deps.append(ReadinessDependency(name="watsonx", ok=watsonx_ok, detail=watsonx_detail))

    failed = [d.name for d in deps if not d.ok]
    payload = ReadinessPayload(
        status="ok" if not failed else "degraded",
        dependencies=deps,
        failed_dependencies=failed,
    )

    if failed:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "ok": False,
                "error": {
                    "code": ErrorCode.CLOUDANT_UPSTREAM.value
                    if "cloudant" in failed
                    else ErrorCode.WATSONX_UPSTREAM.value,
                    "message": f"Not ready — failed: {', '.join(failed)}",
                    "details": payload.model_dump(),
                },
                "request_id": current_request_id(),
            },
        )

    return ok(payload)


@router.get("/version", response_model=Envelope[VersionPayload])
async def version() -> Envelope[VersionPayload]:
    return ok(VersionPayload(**build_info()))
