"""ABEND Archaeologist routes — docs/API.md §8.

The classifier is Bob territory; the analyze handler shells out to it and the
resolve handler is real plumbing on top of audit + learning events.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.dependencies import (
    CurrentUser,
    get_audit_writer,
    get_cloudant,
    get_settings_dep,
    get_watsonx,
)
from app.envelope import Envelope, ok
from app.errors import ErrorCode, HeliosError
from app.logging import get_logger
from app.models.abend import (
    AbendRequest,
    AbendResolveRequest,
    AbendResolveResponse,
    AbendResponse,
    AbendTier,
)
from app.services import abend_classifier
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient
from app.services.watsonx import WatsonxClient, WatsonxError

router = APIRouter()

_log = get_logger("helios.api.abend")


def _build_summary_prompt(result: AbendResponse, raw: str) -> str:
    program = result.failing_step.program or "unknown"
    paragraph = result.source_trace.paragraph or "unknown"
    field = result.source_trace.highlighted_field or "unknown"
    top_causes = ", ".join(c.cause for c in result.ranked_root_causes[:3]) or "n/a"
    return (
        "You are a senior z/OS mainframe engineer explaining an ABEND to a "
        "junior developer.\n\n"
        f"ABEND code: {result.identified_abend.code}\n"
        f"Program: {program}\n"
        f"Failing paragraph: {paragraph}\n"
        f"Failing field: {field}\n"
        f"Known causes from the pattern library: {top_causes}\n\n"
        f"Excerpt of the dump:\n{raw[:1200]}\n\n"
        "In one or two short sentences, explain what likely went wrong and "
        "what the developer should check first. Be specific. No preamble."
    )


@router.post("", response_model=Envelope[AbendResponse])
async def analyze_abend(
    body: AbendRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    watsonx: WatsonxClient = Depends(get_watsonx),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[AbendResponse]:
    result = abend_classifier.classify(
        abend_classifier.AbendInput(
            raw_text=body.raw_text,
            region=body.context.region,
            job_name=body.context.job_name,
        )
    )
    # When watsonx is live and the classifier landed a confirmed/probable
    # tier, ask Granite to refine the business_rule_explanation. Failures
    # leave the deterministic fallback in place — never break the demo on
    # an upstream hiccup.
    if (
        watsonx.is_live
        and not result.degraded
        and result.identified_abend.tier
        in (AbendTier.CONFIRMED, AbendTier.PROBABLE)
    ):
        try:
            prompt = _build_summary_prompt(result, body.raw_text)
            gen = await watsonx.generate(
                prompt,
                model_id=settings.watsonx_chat_model,
                max_new_tokens=160,
                temperature=0.2,
                purpose="abend.business_rule_summary",
            )
            text = (gen.get("generated_text") or "").strip()
            if text:
                # Re-validate to keep the flat aliases (pattern_code/etc) intact.
                payload = result.model_dump()
                payload["business_rule_explanation"] = text
                payload["pattern_code"] = result.identified_abend.code
                payload["confidence"] = result.identified_abend.confidence
                payload["tier"] = result.identified_abend.tier.value
                result = AbendResponse.model_validate(payload)
        except WatsonxError as exc:
            _log.info(
                "abend.granite_summary_failed",
                error=str(exc),
                fallback="deterministic",
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
