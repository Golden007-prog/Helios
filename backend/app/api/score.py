"""Confidence Score routes — docs/API.md §7.

The score endpoint runs the same JJSCAN+ scanner the /api/scan route uses,
detects the backup-gap signal (DELETE-style operations against a target
region's protected resources without a paired UNLOAD/IMAGE COPY/REPRO
step), and feeds both into ``score_engine.compute``.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import ErrorCode, HeliosError
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
from app.services.jjscan import Scanner
from app.services.jjscan.framework import RuleContext
from app.services.jjscan.rules import SEEDED_RULES

router = APIRouter()


_DELETE_TOKEN_RE = re.compile(
    r"\b(?:DELETE|DROP|PURGE|REMOVE)\b", re.IGNORECASE
)
_BACKUP_TOKEN_RE = re.compile(
    r"\b(?:UNLOAD|IMAGE\s+COPY|IMAGECOPY|IDCAMS\s+REPRO|DSNTIAUL|IEBCOPY|XMIT)\b",
    re.IGNORECASE,
)


def _detect_backup_gap(jcl_source: str, protected: list[str]) -> bool:
    """Heuristic: the JCL performs a destructive op against (or near) a
    protected resource and contains no paired backup step. Comment lines
    (``//*``) are stripped before matching so descriptive text like
    "this job has no UNLOAD/IMAGE COPY step" doesn't masquerade as a real
    backup step.
    """
    if not protected:
        return False
    code_lines = [
        line for line in jcl_source.splitlines() if not line.startswith("//*")
    ]
    code = "\n".join(code_lines)
    if not _DELETE_TOKEN_RE.search(code):
        return False
    if _BACKUP_TOKEN_RE.search(code):
        return False
    return True


async def _resolve_jcl_source(
    body: ScoreRequest, cloudant: CloudantClient, shop: str
) -> str:
    if body.jcl_source is not None:
        return body.jcl_source
    if not body.jcl_name:
        return ""
    # Look up the seeded JCL artifact in the requested region first, then
    # fall back to any region (the demo seeds the hero JCL under
    # ``region=int2``; the score endpoint is called with target=int3).
    for region_filter in [{"region": body.region}, {}]:
        result = await cloudant.find(
            "jcl_artifacts",
            {
                "shop": shop,
                "kind": "jcl_artifact",
                "name": body.jcl_name,
                **region_filter,
            },
            limit=1,
        )
        docs = result.get("docs") or []
        if docs:
            return docs[0].get("source", "")
    return ""


@router.post("", response_model=Envelope[ScoreResponse])
async def compute_score(
    body: ScoreRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[ScoreResponse]:
    region = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, body.region, settings.shop),
        body.region,
    )

    raw_source = await _resolve_jcl_source(body, cloudant, settings.shop)
    # Look up the source region (where the JCL was authored) so we can
    # apply substitutions before scanning. The score reflects what the
    # JCL would do *as deployed* in the target region — the simple
    # region-rewrite tokens (DB2 subsystem, HLQ, etc.) are not real
    # findings, so we run scanning against the substituted source.
    scan_source = raw_source
    if raw_source and body.jcl_name:
        # The seed places artifacts under a single source region; if we
        # can resolve it, apply substitutions. Otherwise fall back to the
        # raw source.
        result = await cloudant.find(
            "jcl_artifacts",
            {
                "shop": settings.shop,
                "kind": "jcl_artifact",
                "name": body.jcl_name,
            },
            limit=1,
        )
        artifact_docs = result.get("docs") or []
        if artifact_docs:
            source_region_name = artifact_docs[0].get("region")
            if source_region_name and source_region_name != region.name:
                source_region = await region_atlas.load_region(
                    cloudant, source_region_name, settings.shop
                )
                if source_region is not None:
                    scan_source, _trace = region_atlas.apply_substitutions(
                        raw_source, source_region, region
                    )

    # Run JJSCAN+ to gather findings against the target region.
    findings_payload: list[dict] = []
    if scan_source:
        ctx = RuleContext(
            jcl_source=scan_source,
            target_region=region,
            region_name=region.name,
            jcl_name=body.jcl_name,
            cloudant=cloudant,
            watsonx=None,
        )
        scanner = Scanner(SEEDED_RULES)
        scan_results, _elapsed = scanner.scan(ctx)
        for r in scan_results:
            findings_payload.append(
                {
                    "rule_id": r.rule_id,
                    "severity": r.severity.value,
                    "auto_fixable": r.auto_fix_available,
                    "confidence": 1.0,
                }
            )

    backup_gap = _detect_backup_gap(scan_source, region.protected_resources)

    score_ctx = score_engine.ScoreContext(
        jcl_source=scan_source,
        region_name=region.name,
        region_weights=region.confidence_weight_overrides,
        findings=findings_payload,
        backup_gap=backup_gap,
        region_mismatch_count=0,
        historical_abend_priors={},
    )
    score_value, breakdown = score_engine.compute(findings_payload, score_ctx)
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
