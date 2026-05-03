"""Review Queue routes — docs/API.md §12 + docs/REVIEW_QUEUE.md.

Read endpoints + decisions are real plumbing. The auto-approve policy engine
and the WebSocket broadcaster are wired in :mod:`app.api.ws_queue`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import ErrorCode, HeliosError
from app.models.common import ReviewState
from app.models.queue import (
    QueueDecisionRequest,
    QueueDecisionResponse,
    QueueItem,
    QueueListResponse,
    QueueSinceResponse,
)
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


def _to_queue_item(event: dict) -> QueueItem:
    return QueueItem(
        event_id=event["_id"],
        type=event.get("type", "unknown"),
        initiator=event.get("actor", "unknown"),
        ts=event["ts"],
        state=ReviewState(event.get("extra", {}).get("review_state", "pending_review")),
        confidence_score=event.get("extra", {}).get("confidence_score"),
        summary=event.get("extra", {}),
    )


@router.get("", response_model=Envelope[QueueListResponse])
async def list_queue(
    user: CurrentUser,
    state: ReviewState | None = Query(default=ReviewState.PENDING_REVIEW),
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[QueueListResponse]:
    result = await audit.query(limit=200)
    docs = [
        d
        for d in result.get("docs", [])
        if d.get("extra", {}).get("review_required")
    ]
    if state:
        docs = [
            d
            for d in docs
            if d.get("extra", {}).get("review_state", "pending_review") == state.value
        ]
    items = [_to_queue_item(d) for d in docs]
    pending = sum(1 for d in docs if d.get("extra", {}).get("review_state") in (None, "pending_review"))
    return ok(QueueListResponse(items=items, pending_count=pending, last_seq=None))


@router.post("/{event_id}/approve", response_model=Envelope[QueueDecisionResponse])
async def approve(
    event_id: str,
    body: QueueDecisionRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[QueueDecisionResponse]:
    return await _decide(event_id, body, user, cloudant, audit, settings, ReviewState.APPROVED)


@router.post("/{event_id}/reject", response_model=Envelope[QueueDecisionResponse])
async def reject(
    event_id: str,
    body: QueueDecisionRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[QueueDecisionResponse]:
    return await _decide(event_id, body, user, cloudant, audit, settings, ReviewState.REJECTED)


async def _decide(
    event_id: str,
    body: QueueDecisionRequest,
    user,
    cloudant: CloudantClient,
    audit: AuditWriter,
    settings,
    new_state: ReviewState,
) -> Envelope[QueueDecisionResponse]:
    original = await cloudant.get("audit_log", event_id)
    if not original:
        raise HeliosError(ErrorCode.EVENT_NOT_FOUND, f"No event '{event_id}'")
    if original.get("actor") == user.email:
        raise HeliosError(
            ErrorCode.SELF_REVIEW_FORBIDDEN, "Initiator cannot review their own request"
        )

    now = datetime.now(timezone.utc)
    audit_event = await audit.write_event(
        type=f"review_{new_state.value}",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "reviewer",
        subject=original.get("subject", {}),
        before={"review_state": original.get("extra", {}).get("review_state", "pending_review")},
        after={"review_state": new_state.value},
        extra={
            "for_event_id": event_id,
            "reason": body.reason,
        },
    )
    return ok(
        QueueDecisionResponse(
            event_id=event_id,
            state=new_state,
            decided_by=user.email,
            decided_at=now,
            audit_event_id=audit_event["_id"],
        )
    )


@router.get("/since", response_model=Envelope[QueueSinceResponse])
async def since(
    user: CurrentUser,
    seq: str = Query(...),
    cloudant: CloudantClient = Depends(get_cloudant),
) -> Envelope[QueueSinceResponse]:
    feed = await cloudant.changes("audit_log", since=seq, limit=100)
    items: list[QueueItem] = []
    for change in feed.get("results", []):
        doc = change.get("doc")
        if not doc:
            continue
        if doc.get("extra", {}).get("review_required"):
            items.append(_to_queue_item(doc))
    return ok(
        QueueSinceResponse(items=items, last_seq=str(feed.get("last_seq", seq)))
    )
