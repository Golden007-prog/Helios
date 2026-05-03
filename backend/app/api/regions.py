"""Region Atlas routes — docs/API.md §3.

Read endpoints (GET) are real and serve from Cloudant.
Write endpoints (POST upsert / fork) are real for the persistence layer; the
diff endpoint hands off to the Bob stub.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.models.common import RegionTier
from app.models.region import (
    RegionDiffResponse,
    RegionForkRequest,
    RegionForkResponse,
    RegionListItem,
    RegionListResponse,
    RegionProfile,
    RegionUpsertRequest,
    RegionUpsertResponse,
)
from app.services import region_atlas
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


@router.get("", response_model=Envelope[RegionListResponse])
async def list_regions(
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
    tier: RegionTier | None = Query(default=None),
) -> Envelope[RegionListResponse]:
    profiles = await region_atlas.list_regions(cloudant, settings.shop, tier=tier.value if tier else None)
    items = [RegionListItem(name=p.name, tier=p.tier, hlq=p.hlq) for p in profiles]
    return ok(RegionListResponse(regions=items, total=len(items)))


@router.get("/{name}", response_model=Envelope[RegionProfile])
async def get_region(
    name: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[RegionProfile]:
    profile = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, name, settings.shop), name
    )
    return ok(profile)


@router.post("/{name}", response_model=Envelope[RegionUpsertResponse])
async def upsert_region(
    name: str,
    body: RegionUpsertRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[RegionUpsertResponse]:
    body.profile.name = name  # path is authoritative
    before = await region_atlas.load_region(cloudant, name, settings.shop)
    after = await region_atlas.save_region(cloudant, body.profile, settings.shop)

    review_required = body.profile.tier == RegionTier.PRODUCTION
    event = await audit.write_event(
        type="region_profile_edit",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "region", "name": name},
        before=before.model_dump() if before else None,
        after=after,
        extra={"reason": body.reason, "review_required": review_required},
    )
    return ok(
        RegionUpsertResponse(
            name=name,
            audit_event_id=event["_id"],
            review_required=review_required,
        )
    )


@router.get("/{a}/diff/{b}", response_model=Envelope[RegionDiffResponse])
async def diff_regions(
    a: str,
    b: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[RegionDiffResponse]:
    profile_a = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, a, settings.shop), a
    )
    profile_b = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, b, settings.shop), b
    )
    return ok(region_atlas.diff_regions(profile_a, profile_b))


@router.post("/{name}/forks/{job_name}", response_model=Envelope[RegionForkResponse])
async def fork_region(
    name: str,
    job_name: str,
    body: RegionForkRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[RegionForkResponse]:
    base = region_atlas.must_exist(
        await region_atlas.load_region(cloudant, name, settings.shop), name
    )
    fork_doc = {
        "kind": "region_override",
        "schema_version": "1.0",
        "shop": settings.shop,
        "region": name,
        "job_name": job_name,
        "overrides": body.overrides,
        "base_name": base.name,
    }
    stored = await cloudant.put("regions", fork_doc)
    event = await audit.write_event(
        type="region_profile_edit",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "region_override", "name": name, "job_name": job_name},
        after=stored,
        extra={"reason": body.reason},
    )
    return ok(
        RegionForkResponse(
            region=name,
            job_name=job_name,
            audit_event_id=event["_id"],
        )
    )
