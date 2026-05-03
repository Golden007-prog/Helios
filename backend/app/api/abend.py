"""ABEND Archaeologist routes — docs/API.md §8.

The classifier is Bob territory; the analyze handler shells out to it and the
resolve handler is real plumbing on top of audit + learning events.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import BobStubError, ErrorCode, HeliosError
from app.models.abend import (
    AbendRequest,
    AbendResolveRequest,
    AbendResolveResponse,
    AbendResponse,
)
from app.services import abend_classifier
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


@router.post("", response_model=Envelope[AbendResponse])
async def analyze_abend(
    body: AbendRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[AbendResponse]:
    # Bob stub — surfaces 501 with BOB marker via the NotImplementedError handler.
    result = abend_classifier.classify(
        abend_classifier.AbendInput(
            raw_text=body.raw_text,
            region=body.context.region,
            job_name=body.context.job_name,
        )
    )
    return ok(result)


@router.post("/{event_id}/resolve", response_model=Envelope[AbendResolveResponse])
async def resolve_abend(
    event_id: str,
    body: AbendResolveRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[AbendResolveResponse]:
    original = await cloudant.get("audit_log", event_id)
    if not original:
        raise HeliosError(ErrorCode.EVENT_NOT_FOUND, f"No event '{event_id}'")

    audit_event = await audit.write_event(
        type="abend_resolve",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject=original.get("subject", {}),
        before=original,
        after={
            "root_cause_choice": body.root_cause_choice,
            "applied_runbook_id": body.applied_runbook_id,
            "outcome": body.outcome,
        },
        extra={"notes": body.notes},
    )
    now = datetime.now(timezone.utc)
    learning_doc = {
        "kind": "learning_event",
        "schema_version": "1.0",
        "shop": settings.shop,
        "type": (
            "feedback_abend_resolved"
            if body.outcome == "resolved"
            else "feedback_abend_did_not_resolve"
        ),
        "abend_event_id": event_id,
        "root_cause_choice": body.root_cause_choice,
        "applied_runbook_id": body.applied_runbook_id,
        "actor": user.email,
        "ts": now.isoformat(),
        "ts_unix_ms": int(now.timestamp() * 1000),
    }
    learning_stored = await cloudant.put("learning", learning_doc)

    return ok(
        AbendResolveResponse(
            event_id=event_id,
            audit_event_id=audit_event["_id"],
            learning_event_id=learning_stored["_id"],
        )
    )
