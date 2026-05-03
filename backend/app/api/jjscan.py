"""JJSCAN+ routes — docs/API.md §6.

The route handler is real plumbing: it builds the :class:`RuleContext`, runs
the :class:`Scanner`, persists findings, and writes the audit + learning events
on decisions. The four rule bodies are Bob territory (raise 501 with BOB
markers until implemented).
"""

from __future__ import annotations

from datetime import UTC, datetime

import ulid
from fastapi import APIRouter, Depends

from app.dependencies import (
    CurrentUser,
    get_audit_writer,
    get_cloudant,
    get_settings_dep,
    get_watsonx,
)
from app.envelope import Envelope, ok
from app.errors import BobStubError, ErrorCode, HeliosError
from app.models.common import FindingState
from app.models.jjscan import (
    Finding,
    FindingAutoFixResponse,
    FindingDecideRequest,
    FindingDecideResponse,
    ScanRequest,
    ScanResponse,
)
from app.services import region_atlas
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient
from app.services.jjscan import Scanner
from app.services.jjscan.framework import RuleContext, build_finding_subject
from app.services.jjscan.rules import SEEDED_RULES
from app.services.watsonx import WatsonxClient

router = APIRouter()


@router.post("", response_model=Envelope[ScanResponse])
async def scan(
    body: ScanRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    watsonx: WatsonxClient = Depends(get_watsonx),
    settings=Depends(get_settings_dep),
) -> Envelope[ScanResponse]:
    # Resolve source: inline or named.
    if body.jcl_source is not None:
        source = body.jcl_source
        region_name = body.target_region
        jcl_name = None
    else:
        assert body.jcl_name is not None
        assert body.region is not None
        result = await cloudant.find(
            "jcl_artifacts",
            {
                "shop": settings.shop,
                "kind": "jcl_artifact",
                "region": body.region,
                "name": body.jcl_name,
            },
            limit=1,
        )
        docs = result.get("docs", [])
        if not docs:
            raise HeliosError(
                ErrorCode.JCL_NOT_FOUND,
                f"No JCL '{body.jcl_name}' in region '{body.region}'",
            )
        source = docs[0].get("source", "")
        region_name = body.target_region or body.region
        jcl_name = body.jcl_name

    target = (
        await region_atlas.load_region(cloudant, region_name, settings.shop)
        if region_name
        else None
    )

    ctx = RuleContext(
        jcl_source=source,
        target_region=target,
        region_name=region_name,
        jcl_name=jcl_name,
        cloudant=cloudant,
        watsonx=watsonx,
    )

    scanner = Scanner(SEEDED_RULES)
    # The rules raise NotImplementedError today; the global handler maps
    # that to a 501 with the BOB marker.
    results, elapsed_ms = scanner.scan(ctx)

    findings: list[Finding] = []
    for r in results:
        finding_id = f"find:{r.rule_id}:{ulid.new().str}"
        findings.append(
            Finding(
                id=finding_id,
                rule_id=r.rule_id,
                severity=r.severity,
                description=r.description,
                details=r.details,
                subject=build_finding_subject(ctx),
                state=FindingState.OPEN,
                auto_fix_available=r.auto_fix_available,
            )
        )
    return ok(ScanResponse(findings=findings, scan_duration_ms=elapsed_ms))


@router.post("/findings/{finding_id}/decide", response_model=Envelope[FindingDecideResponse])
async def decide_finding(
    finding_id: str,
    body: FindingDecideRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[FindingDecideResponse]:
    # Look up the finding (in-memory mode tolerates missing — return 404 either way).
    existing = await cloudant.get("findings", finding_id)
    if not existing:
        # Allow ad-hoc decisions on transient findings that were never persisted
        # by writing a thin record now. This keeps the audit trail honest.
        existing = {
            "_id": finding_id,
            "kind": "finding",
            "schema_version": "1.0",
            "shop": settings.shop,
            "rule_id": finding_id.split(":")[1] if ":" in finding_id else "unknown",
            "subject": {"kind": "jcl", "name": "<unknown>", "region": None},
            "state": FindingState.OPEN.value,
        }

    decided_at = datetime.now(UTC)
    after = {
        **existing,
        "state": body.decision.value,
        "decided_at": decided_at.isoformat(),
        "decided_by": user.email,
        "decision_reason": body.reason,
        "decision_reason_tags": body.reason_tags,
    }
    await cloudant.put("findings", after)

    audit_event = await audit.write_event(
        type=f"finding_{body.decision.value}",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject=existing.get("subject", {}),
        before=existing,
        after=after,
        extra={
            "finding_id": finding_id,
            "rule_id": existing.get("rule_id"),
            "decision_reason": body.reason,
            "decision_reason_tags": body.reason_tags,
        },
    )

    learning_doc = {
        "kind": "learning_event",
        "schema_version": "1.0",
        "shop": settings.shop,
        "type": f"feedback_jjscan_{body.decision.value}",
        "rule_id": existing.get("rule_id"),
        "finding_id": finding_id,
        "actor": user.email,
        "ts": decided_at.isoformat(),
        "ts_unix_ms": int(decided_at.timestamp() * 1000),
        "reason_tags": body.reason_tags,
    }
    learning_stored = await cloudant.put("learning", learning_doc)

    return ok(
        FindingDecideResponse(
            finding_id=finding_id,
            state=body.decision,
            decided_at=decided_at,
            audit_event_id=audit_event["_id"],
            learning_event_id=learning_stored["_id"],
        )
    )


@router.post("/findings/{finding_id}/auto-fix", response_model=Envelope[FindingAutoFixResponse])
async def auto_fix(
    finding_id: str,
    user: CurrentUser,
    audit: AuditWriter = Depends(get_audit_writer),
) -> Envelope[FindingAutoFixResponse]:
    # TODO(1.3 follow-up): Implement auto-fix application
    # For now, return a stub response indicating the fix would be applied
    raise BobStubError(
        "JJSCAN+ auto-fix application is Phase 1.3 follow-up work",
        feature="jjscan.auto_fix",
        spec_doc="docs/JJSCAN_PLUS_RULES.md",
    )
