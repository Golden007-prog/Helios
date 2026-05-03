"""Confidence Score routes — docs/API.md §7.

Weights GET / POST and override are real (plumbing). The compute call delegates
to the Bob stub; once filled in, the score POST returns the engine output as-is.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import BobStubError, ErrorCode, HeliosError
from app.models.common import RegionTier
from app.models.score import (
    ScoreOverrideRequest,
    ScoreOverrideResponse,
    ScoreRequest,
    ScoreResponse,
    WeightsResponse,
    WeightsUpdateRequest,
    WeightsUpdateResponse,
)
from app.services import region_atlas, score as score_engine
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


@router.post("", response_model=Envelope[ScoreResponse])
async def compute_score(
    body: ScoreRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[ScoreResponse]:
    region = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, body.region, settings.shop), body.region
    )
    ctx = score_engine.ScoreContext(
        jcl_source=body.jcl_source or "",
        region_name=region.name,
        region_weights={**score_engine.default_weights(), **region.confidence_weight_overrides},
        findings=[],
        backup_gap=False,
        region_mismatch_count=0,
        historical_abend_priors={},
    )
    # Bob stub raises here; mapped to 501 + BOB by the global handler.
    score_value, breakdown = score_engine.compute([], ctx)
    return ok(ScoreResponse(score=score_value, breakdown=breakdown))


@router.get("/weights/{region}", response_model=Envelope[WeightsResponse])
async def get_weights(
    region: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[WeightsResponse]:
    region_doc = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, region, settings.shop), region
    )
    defaults = score_engine.default_weights()
    overrides = region_doc.confidence_weight_overrides
    merged = {**defaults, **overrides}
    source = "merged" if overrides else "default"
    return ok(WeightsResponse(region=region, weights=merged, source=source))


@router.post("/weights/{region}", response_model=Envelope[WeightsUpdateResponse])
async def update_weights(
    region: str,
    body: WeightsUpdateRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[WeightsUpdateResponse]:
    region_doc = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, region, settings.shop), region
    )
    before = region_doc.confidence_weight_overrides.copy()
    region_doc.confidence_weight_overrides = body.weights
    await region_atlas.save_region(cloudant, region_doc, settings.shop)
    review_required = region_doc.tier == RegionTier.PRODUCTION
    event = await audit.write_event(
        type="score_weights_edit",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "region", "name": region},
        before={"weights": before},
        after={"weights": body.weights},
        extra={"reason": body.reason, "review_required": review_required},
    )
    return ok(
        WeightsUpdateResponse(
            region=region,
            weights=body.weights,
            audit_event_id=event["_id"],
            review_required=review_required,
        )
    )


@router.post("/{event_id}/override", response_model=Envelope[ScoreOverrideResponse])
async def override_score(
    event_id: str,
    body: ScoreOverrideRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[ScoreOverrideResponse]:
    # Look up the original event to record `original_score`.
    original = await cloudant.get("audit_log", event_id)
    if not original:
        raise HeliosError(ErrorCode.EVENT_NOT_FOUND, f"No event '{event_id}'")
    original_score = original.get("extra", {}).get("confidence_score") or original.get(
        "after", {}
    ).get("current_confidence_score") or 0

    audit_event = await audit.write_event(
        type="score_override",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject=original.get("subject", {}),
        before={"score": original_score},
        after={"score": body.new_score},
        extra={"reason": body.reason, "original_event_id": event_id},
    )
    learning_doc = {
        "kind": "learning_event",
        "schema_version": "1.0",
        "shop": settings.shop,
        "type": "feedback_score_override",
        "original_event_id": event_id,
        "original_score": original_score,
        "new_score": body.new_score,
        "reason": body.reason,
        "actor": user.email,
        "ts": audit_event["ts"],
        "ts_unix_ms": audit_event["ts_unix_ms"],
    }
    learning_stored = await cloudant.put("learning", learning_doc)

    return ok(
        ScoreOverrideResponse(
            event_id=event_id,
            original_score=original_score,
            new_score=body.new_score,
            audit_event_id=audit_event["_id"],
            learning_event_id=learning_stored["_id"],
        )
    )
