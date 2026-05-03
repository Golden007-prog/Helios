"""Promote (the hero endpoint) — docs/API.md §5.

The handler does the work that doesn't require Bob's hero algorithms
(load + audit + auto-approve gate) and delegates the diff + scoring + auto-fix
math to Bob's stubs (which raise 501 with BOB markers until implemented).

Once Bob lands :func:`region_atlas.diff_regions`, :func:`score.compute`, and
the substitution engine, this route's full happy path turns green with no
changes here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import BobStubError, ErrorCode, HeliosError
from app.models.common import ReviewState
from app.models.promote import (
    PromoteCancelResponse,
    PromoteRequest,
    PromoteResponse,
)
from app.services import region_atlas
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


@router.post("", response_model=Envelope[PromoteResponse])
async def promote(
    body: PromoteRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[PromoteResponse]:
    source = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, body.source_region, settings.shop),
        body.source_region,
    )
    target = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, body.target_region, settings.shop),
        body.target_region,
    )

    # Diff + score are Bob territory — surface their 501 markers cleanly.
    diff = region_atlas.diff_regions(source, target)  # raises BobStubError today

    # Bob will fill in the score/auto-fix blocks; we still want the audit
    # event for the *attempt* to be written so the chain stays continuous.
    raise BobStubError(
        "Promote pipeline depends on diff/scoring/auto-fix engines reserved for Bob",
        feature="promote.execute",
        spec_doc="docs/PHASE_PLAN.md §1.3",
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
