"""Audit log query routes — docs/API.md §10.

Bundle export and the daily attestation are queue-backed (the actual tar.gz
generation is async via the JobRunner). The chain root attestation read is
real but the per-day rollup is computed by a nightly job (Bob's worklist
includes wiring it; the read endpoint here serves whatever it has produced).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import (
    CurrentUser,
    get_audit_writer,
    get_cloudant,
    get_job_runner_dep,
    get_settings_dep,
)
from app.envelope import Envelope, ok
from app.errors import ErrorCode, HeliosError
from app.jobs.runner import JobRunner
from app.models.audit import (
    AttestationResponse,
    AuditBundleRequest,
    AuditBundleResponse,
    AuditBundleStatusResponse,
    AuditEvent,
    AuditQueryResponse,
)
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


@router.get("", response_model=Envelope[AuditQueryResponse])
async def query_audit(
    user: CurrentUser,
    subject_kind: str | None = Query(default=None),
    subject_name: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    type: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    cursor: str | None = Query(default=None),
    audit: AuditWriter = Depends(get_audit_writer),
) -> Envelope[AuditQueryResponse]:
    result = await audit.query(
        subject_kind=subject_kind,
        subject_name=subject_name,
        actor=actor,
        type=type,
        since_ms=int(from_.timestamp() * 1000) if from_ else None,
        until_ms=int(to.timestamp() * 1000) if to else None,
        limit=limit,
        bookmark=cursor,
    )
    return ok(
        AuditQueryResponse(
            events=[AuditEvent.model_validate(d) for d in result.get("docs", [])],
            bookmark=result.get("bookmark"),
        )
    )


@router.get("/{event_id}", response_model=Envelope[AuditEvent])
async def get_audit_event(
    event_id: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
) -> Envelope[AuditEvent]:
    doc = await cloudant.get("audit_log", event_id)
    if not doc:
        raise HeliosError(ErrorCode.EVENT_NOT_FOUND, f"No event '{event_id}'")
    return ok(AuditEvent.model_validate(doc))


@router.post("/bundle", response_model=Envelope[AuditBundleResponse])
async def request_bundle(
    body: AuditBundleRequest,
    user: CurrentUser,
    runner: JobRunner = Depends(get_job_runner_dep),
) -> Envelope[AuditBundleResponse]:
    job = await runner.enqueue(
        kind="audit_bundle",
        payload=body.model_dump(by_alias=True, exclude_none=True),
        actor=user.email,
    )
    return ok(AuditBundleResponse(bundle_job_id=job.id))


@router.get("/bundle/{job_id}", response_model=Envelope[AuditBundleStatusResponse])
async def bundle_status(
    job_id: str,
    user: CurrentUser,
    runner: JobRunner = Depends(get_job_runner_dep),
) -> Envelope[AuditBundleStatusResponse]:
    job = await runner.get(job_id)
    if not job:
        raise HeliosError(ErrorCode.EVENT_NOT_FOUND, f"No bundle job '{job_id}'")
    return ok(
        AuditBundleStatusResponse(
            bundle_job_id=job.id,
            state=job.state.value,
            download_url=job.result.get("download_url") if job.result else None,
            error=job.error,
        )
    )


@router.get("/attestation/{date}", response_model=Envelope[AttestationResponse])
async def attestation(
    date: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[AttestationResponse]:
    """Read the daily chain root attestation written by ``audit_chain_verify``."""
    doc_id = f"att:{date}"
    doc = await cloudant.get("audit_log", doc_id)
    if not doc:
        # Compute on-the-fly fallback for in-memory mode + dev: walk events
        # for the day and return the last hash.
        result = await cloudant.find(
            "audit_log",
            {"shop": settings.shop, "kind": "audit_event"},
            limit=200,
            sort=[{"ts_unix_ms": "asc"}],
        )
        events: list[dict[str, Any]] = [
            d for d in result.get("docs", []) if str(d.get("ts", "")).startswith(date)
        ]
        if not events:
            raise HeliosError(
                ErrorCode.EVENT_NOT_FOUND,
                f"No attestation for {date} (no audit events)",
            )
        last = events[-1]
        return ok(
            AttestationResponse(
                date=date,
                chain_root_hash=last.get("chain", {}).get("this_event_hash", ""),
                event_count=len(events),
            )
        )
    return ok(
        AttestationResponse(
            date=date,
            chain_root_hash=doc["chain_root_hash"],
            event_count=doc["event_count"],
        )
    )
