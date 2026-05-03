"""Promote (the hero endpoint) — docs/API.md §5.

The handler orchestrates the full promote pipeline: diff, substitution,
JJSCAN+, scoring, auto-fixes, and audit logging.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import BobStubError, ErrorCode, HeliosError
from app.models.common import ReviewState
from app.models.promote import (
    AutoFix,
    PromoteCancelResponse,
    PromoteRequest,
    PromoteResponse,
)
from app.services import region_atlas
from app.services.audit_writer import AuditWriter
from app.services.backup_generator import BackupRequest, generate
from app.services.cloudant import CloudantClient
from app.services.jjscan.framework import RuleContext, Scanner
from app.services.jjscan.rules import SEEDED_RULES
from app.services.score import ScoreContext, compute

router = APIRouter()


@router.post("", response_model=Envelope[PromoteResponse])
async def promote(
    body: PromoteRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[PromoteResponse]:
    """Execute the full promote pipeline."""
    # 1. Load source + target regions
    source = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, body.source_region, settings.shop),
        body.source_region,
    )
    target = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, body.target_region, settings.shop),
        body.target_region,
    )

    # 2. Load JCL source — seed_demo writes hero JCL into ``jcl_artifacts``.
    jcl_result = await cloudant.find(
        "jcl_artifacts",
        {
            "shop": settings.shop,
            "kind": "jcl_artifact",
            "name": body.jcl_name,
        },
        limit=1,
    )
    if not jcl_result.get("docs"):
        raise HeliosError(ErrorCode.JCL_NOT_FOUND, f"No JCL named '{body.jcl_name}'")
    jcl_doc = jcl_result["docs"][0]
    jcl_source = jcl_doc.get("source", "")

    # 3. Run region diff
    diff_response = region_atlas.diff_regions(source, target)

    # 4. Apply substitutions to JCL
    rewritten_jcl, substitution_trace = region_atlas.apply_substitutions(jcl_source, source, target)

    # 5. Run JJSCAN+ rules on rewritten JCL
    scanner = Scanner(SEEDED_RULES)
    rule_ctx = RuleContext(
        jcl_source=rewritten_jcl,
        target_region=target,
        region_name=target.name,
        jcl_name=body.jcl_name,
        cloudant=cloudant,
        watsonx=None,  # Not needed for Phase 1 rules
    )
    rule_results, scan_duration_ms = scanner.scan(rule_ctx)

    # Convert rule results to findings format
    findings = [
        {
            "rule_id": r.rule_id,
            "severity": r.severity.value,
            "description": r.description,
            "details": r.details,
            "auto_fixable": r.auto_fix_available,
        }
        for r in rule_results
    ]

    # 6. Determine backup gap
    # Check if JCL touches protected resources without backup
    backup_gap = False
    if target.protected_resources:
        # Simple heuristic: if any protected resource appears in JCL
        for resource in target.protected_resources:
            if resource.upper() in jcl_source.upper():
                # Check if backup is requested
                if "generate_paired_backup" not in body.auto_apply_fixes:
                    backup_gap = True
                break

    # 7. Compute confidence score
    score_ctx = ScoreContext(
        jcl_source=rewritten_jcl,
        region_name=target.name,
        region_weights=target.confidence_weight_overrides,
        findings=findings,
        backup_gap=backup_gap,
        region_mismatch_count=0,  # Would check against target.protected_resources
        historical_abend_priors={},  # Would query audit log
    )
    confidence_score, score_breakdown = compute(findings, score_ctx)

    # 8. Apply auto-fixes
    auto_fixes_applied: list[AutoFix] = []
    auto_fixes_available: list[AutoFix] = []

    if "generate_paired_backup" in body.auto_apply_fixes and backup_gap:
        # Generate backup JCL for protected resources
        for resource in target.protected_resources:
            if resource.upper() in jcl_source.upper():
                backup_req = BackupRequest(
                    protected_resource=resource,
                    region_hlq=target.hlq,
                    job_name=body.jcl_name,
                    timestamp=datetime.utcnow(),
                )
                backup_artifact = generate(backup_req)
                auto_fixes_applied.append(
                    AutoFix(
                        fix="generate_paired_backup",
                        target=resource,
                        details={
                            "backup_dsn": backup_artifact.backup_dataset_name,
                            "method": backup_artifact.method,
                            "jcl": backup_artifact.jcl_text,
                        },
                    )
                )

    # Check for available but not applied fixes
    for finding in findings:
        if finding.get("auto_fixable") and "update_syslib" not in body.auto_apply_fixes:
            auto_fixes_available.append(
                AutoFix(
                    fix="update_syslib",
                    target=finding.get("details", {}).get("copybook", ""),
                    details=finding.get("details", {}),
                )
            )

    # 9. Write audit event
    audit_event = await audit.write_event(
        type="jcl.promote",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "jcl", "name": body.jcl_name},
        before={"source": jcl_source, "region": body.source_region},
        after={"source": rewritten_jcl, "region": body.target_region},
        extra={
            "confidence_score": confidence_score,
            "findings_count": len(findings),
            "auto_fixes_applied": len(auto_fixes_applied),
            "reason": body.reason or "Promote via API",
        },
    )

    # 10. Determine review state
    if confidence_score >= target.review.auto_approve_threshold:
        state = ReviewState.APPROVED
    elif confidence_score >= 60:
        state = ReviewState.PENDING_REVIEW
    else:
        state = ReviewState.REJECTED

    # The PromoteResponse model expects ``confidence_breakdown`` as a flat
    # ``dict[str, int|float]``; flatten the rich ScoreBreakdown into that.
    flat_breakdown: dict[str, int | float] = {"base": score_breakdown.base}
    for k, v in score_breakdown.deductions.items():
        flat_breakdown[f"deduction.{k}"] = v
    for k, v in score_breakdown.boosts.items():
        flat_breakdown[f"boost.{k}"] = v

    return ok(
        PromoteResponse(
            promote_event_id=audit_event["_id"],
            audit_event_id=audit_event["_id"],
            diff=[f.model_dump() for f in diff_response.fields],
            confidence_score=confidence_score,
            confidence_breakdown=flat_breakdown,
            auto_fixes_applied=auto_fixes_applied,
            auto_fixes_available_but_not_applied=auto_fixes_available,
            state=state,
            reviewer=None if state == ReviewState.APPROVED else "required",
        )
    )


@router.get("/{event_id}", response_model=Envelope[PromoteResponse])
async def get_promote(
    event_id: str,
    user: CurrentUser,
    audit: AuditWriter = Depends(get_audit_writer),
) -> Envelope[PromoteResponse]:
    raise BobStubError(
        "Promote status read depends on the promote write path landing first",
        feature="promote.get",
        spec_doc="docs/API.md §5",
    )


@router.post("/{event_id}/cancel", response_model=Envelope[PromoteCancelResponse])
async def cancel_promote(
    event_id: str,
    user: CurrentUser,
    audit: AuditWriter = Depends(get_audit_writer),
) -> Envelope[PromoteCancelResponse]:
    # Cancellation flow is plumbing, but the underlying state machine lives
    # alongside the Bob promote impl, so we surface the same marker.
    raise BobStubError(
        "Promote cancel depends on the promote state machine",
        feature="promote.cancel",
        spec_doc="docs/API.md §5",
    )
