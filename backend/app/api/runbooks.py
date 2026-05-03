"""Runbook routes — docs/API.md §9.

Pure plumbing on top of Cloudant — no Bob stubs in this module.
"""

from __future__ import annotations

import ulid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import ErrorCode, HeliosError
from app.models.runbook import (
    Runbook,
    RunbookApplyRequest,
    RunbookApplyResponse,
    RunbookCreateRequest,
    RunbookCreateResponse,
    RunbookListResponse,
)
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


def _doc_to_runbook(doc: dict) -> Runbook:
    cleaned = {k: v for k, v in doc.items() if k not in {"_id", "_rev", "kind", "schema_version", "shop"}}
    cleaned["id"] = doc["_id"]
    return Runbook.model_validate(cleaned)


@router.get("", response_model=Envelope[RunbookListResponse])
async def list_runbooks(
    user: CurrentUser,
    abend_code: str = Query(...),
    program: str | None = Query(default=None),
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[RunbookListResponse]:
    selector: dict = {
        "shop": settings.shop,
        "kind": "runbook",
        "applies_to.abend_code": abend_code,
    }
    if program:
        selector["applies_to.program"] = program
    result = await cloudant.find(
        "runbooks",
        selector,
        limit=20,
        sort=[{"success_count": "desc"}],
    )
    runbooks = [_doc_to_runbook(d) for d in result.get("docs", [])]
    return ok(RunbookListResponse(runbooks=runbooks, total=len(runbooks)))


@router.get("/{runbook_id}", response_model=Envelope[Runbook])
async def get_runbook(
    runbook_id: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
) -> Envelope[Runbook]:
    doc = await cloudant.get("runbooks", runbook_id)
    if not doc:
        raise HeliosError(ErrorCode.RUNBOOK_NOT_FOUND, f"No runbook '{runbook_id}'")
    return ok(_doc_to_runbook(doc))


@router.post("", response_model=Envelope[RunbookCreateResponse])
async def create_runbook(
    body: RunbookCreateRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[RunbookCreateResponse]:
    runbook_id = (
        f"runbook:{body.applies_to[0].abend_code}:{ulid.new().str}"
        if body.applies_to
        else f"runbook:misc:{ulid.new().str}"
    )
    doc: dict = {
        "_id": runbook_id,
        "kind": "runbook",
        "schema_version": "1.0",
        "shop": settings.shop,
        "title": body.title,
        "applies_to": [a.model_dump() for a in body.applies_to],
        "body_markdown": body.body_markdown,
        "fix_actions": [f.model_dump() for f in body.fix_actions],
        "created_by": user.email,
        "success_count": 0,
        "failure_count": 0,
    }
    stored = await cloudant.put("runbooks", doc)
    event = await audit.write_event(
        type="runbook_create",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "runbook", "name": body.title},
        after=stored,
        extra={"runbook_id": runbook_id},
    )
    return ok(
        RunbookCreateResponse(
            runbook=_doc_to_runbook(stored),
            audit_event_id=event["_id"],
        )
    )


@router.post("/{runbook_id}/apply", response_model=Envelope[RunbookApplyResponse])
async def apply_runbook(
    runbook_id: str,
    body: RunbookApplyRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[RunbookApplyResponse]:
    doc = await cloudant.get("runbooks", runbook_id)
    if not doc:
        raise HeliosError(ErrorCode.RUNBOOK_NOT_FOUND, f"No runbook '{runbook_id}'")

    application_id = f"app:{ulid.new().str}"
    now = datetime.now(timezone.utc)
    doc["last_applied_at"] = now.isoformat()
    await cloudant.put("runbooks", doc)

    await audit.write_event(
        type="runbook_apply",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "runbook", "name": doc.get("title", runbook_id)},
        extra={
            "runbook_id": runbook_id,
            "application_id": application_id,
            "for_event_id": body.event_id,
            "notes": body.notes,
        },
    )
    return ok(RunbookApplyResponse(runbook_id=runbook_id, application_id=application_id))
