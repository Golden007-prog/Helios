"""Learning Loop query routes — docs/API.md §11.

Read-only aggregation endpoints; the writes happen as side effects of
``decide_finding``, ``override_score``, and ``resolve_abend``. All real plumbing.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.models.learning import (
    AbendPriorEntry,
    AbendPriorsResponse,
    DissentResponse,
    RunbookRankEntry,
    RunbookRankResponse,
)
from app.services.cloudant import CloudantClient

router = APIRouter()


@router.get("/dissent", response_model=Envelope[DissentResponse])
async def dissent(
    user: CurrentUser,
    rule_id: str = Query(...),
    region: str | None = Query(default=None),
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[DissentResponse]:
    selector: dict[str, Any] = {"shop": settings.shop, "rule_id": rule_id}
    result = await cloudant.find("learning", selector, limit=200)
    docs = result.get("docs", [])
    dismiss = [d for d in docs if d.get("type") == "feedback_jjscan_dismissed"]
    accept = [d for d in docs if d.get("type") == "feedback_jjscan_accepted"]
    common: list[str] = []
    if dismiss:
        tags: list[str] = []
        for d in dismiss:
            tags.extend(d.get("reason_tags", []))
        common = [t for t, _ in Counter(tags).most_common(3)]
    return ok(
        DissentResponse(
            rule_id=rule_id,
            region=region,
            dissent_count=len(dismiss),
            dissent_total=len(dismiss) + len(accept),
            common_reasons=common,
        )
    )


@router.get("/abend-priors", response_model=Envelope[AbendPriorsResponse])
async def abend_priors(
    user: CurrentUser,
    abend_code: str = Query(...),
    program: str | None = Query(default=None),
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[AbendPriorsResponse]:
    selector: dict[str, Any] = {
        "shop": settings.shop,
        "kind": "abend_pattern",
        "abend_code": abend_code,
    }
    if program:
        selector["program"] = program
    result = await cloudant.find("abend_patterns", selector, limit=20)
    priors = [
        AbendPriorEntry(
            cause=d.get("cause", "unknown"),
            prior_count=d.get("prior_count", 0),
            confidence=float(d.get("confidence", 0.0)),
        )
        for d in result.get("docs", [])
    ]
    priors.sort(key=lambda p: (-p.prior_count, -p.confidence))
    return ok(AbendPriorsResponse(abend_code=abend_code, program=program, priors=priors))


@router.get("/runbook-rank", response_model=Envelope[RunbookRankResponse])
async def runbook_rank(
    user: CurrentUser,
    abend_code: str = Query(...),
    program: str | None = Query(default=None),
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[RunbookRankResponse]:
    selector: dict[str, Any] = {
        "shop": settings.shop,
        "kind": "runbook",
        "applies_to.abend_code": abend_code,
    }
    if program:
        selector["applies_to.program"] = program
    result = await cloudant.find("runbooks", selector, limit=20)
    runbooks = [
        RunbookRankEntry(
            runbook_id=d["_id"],
            title=d.get("title", "(untitled)"),
            success_count=d.get("success_count", 0),
            failure_count=d.get("failure_count", 0),
        )
        for d in result.get("docs", [])
    ]
    runbooks.sort(key=lambda r: (-r.success_count, r.failure_count))
    return ok(
        RunbookRankResponse(abend_code=abend_code, program=program, runbooks=runbooks)
    )
