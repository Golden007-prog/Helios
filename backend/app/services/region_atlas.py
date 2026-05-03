"""Region Atlas — schema validator + diff engine + substitution engine.

Status:

* :func:`load_region` / :func:`save_region` — real, plumbing only.
* :func:`diff_regions` — **STUB** (Bob, Phase 1.2).
* :func:`apply_substitutions` — **STUB** (Bob, Phase 1.2).

The diff engine and substitution engine are the hero of Region Atlas; they
must show meaningful Bob session work.
"""

from __future__ import annotations

from typing import Any

from app.errors import BobStubError, ErrorCode, HeliosError
from app.models.region import RegionDiffResponse, RegionProfile
from app.services.cloudant import CloudantClient

DB_SHORT = "regions"


async def load_region(cloudant: CloudantClient, name: str, shop: str) -> RegionProfile | None:
    """Look up a region by name. Returns None if not found."""
    result = await cloudant.find(
        DB_SHORT,
        {"shop": shop, "kind": "region", "name": name},
        limit=1,
    )
    docs = result.get("docs", [])
    if not docs:
        return None
    doc = docs[0]
    # Cloudant fields the model doesn't expect — drop them here.
    for k in ("_id", "_rev", "kind", "schema_version", "shop"):
        doc.pop(k, None)
    return RegionProfile.model_validate(doc)


async def list_regions(
    cloudant: CloudantClient, shop: str, *, tier: str | None = None
) -> list[RegionProfile]:
    sel: dict[str, Any] = {"shop": shop, "kind": "region"}
    if tier:
        sel["tier"] = tier
    result = await cloudant.find(DB_SHORT, sel, limit=100)
    out: list[RegionProfile] = []
    for doc in result.get("docs", []):
        for k in ("_id", "_rev", "kind", "schema_version", "shop"):
            doc.pop(k, None)
        out.append(RegionProfile.model_validate(doc))
    return out


async def save_region(
    cloudant: CloudantClient, profile: RegionProfile, shop: str
) -> dict[str, Any]:
    """Upsert by region name. Returns the persisted document."""
    existing = await cloudant.find(
        DB_SHORT,
        {"shop": shop, "kind": "region", "name": profile.name},
        limit=1,
    )
    doc: dict[str, Any] = {
        "kind": "region",
        "schema_version": "1.0",
        "shop": shop,
        **profile.model_dump(by_alias=True, exclude_none=False),
    }
    if existing.get("docs"):
        old = existing["docs"][0]
        doc["_id"] = old["_id"]
        doc["_rev"] = old.get("_rev")
    return await cloudant.put(DB_SHORT, doc)


def diff_regions(a: RegionProfile, b: RegionProfile) -> RegionDiffResponse:
    """Field-by-field structural diff between two region profiles.

    BOB: implement the diff that powers the Region Atlas hero shot.

    Required behavior (per docs/PHASE_PLAN.md §1.2 exit criteria):

    * Walk both profiles to produce an ordered list of :class:`DiffField`
      with ``kind`` ∈ {``value_change``, ``added``, ``removed``}.
    * Diff between ``int2`` and ``int3`` of the seeded corpus must surface
      exactly 7 highlighted fields per ``docs/PERSONA_MAYA.md`` Scene 1.
    * Diff must complete in well under 250 ms for two seeded profiles.
    """
    raise BobStubError(
        "Region Atlas diff engine is reserved for Bob",
        feature="region_atlas.diff_regions",
        spec_doc="docs/PHASE_PLAN.md §1.2",
    )


def apply_substitutions(
    jcl_source: str,
    source_region: RegionProfile,
    target_region: RegionProfile,
) -> str:
    """Rewrite ``jcl_source`` so its region-specific fields match ``target_region``.

    BOB: implement the substitution engine that backs the Promote flow.

    Required behavior (per docs/JJSCAN_PLUS_RULES.md and docs/REGION_PROFILE_SCHEMA.md):

    * Substitute HLQ, DB2 subsystem id, plan collection, RACF group, JES
      class, scheduler queue, volser pattern.
    * Preserve JCL formatting (column 72 wrap, comment continuations).
    * Emit a structured trace of every substitution applied — the Promote
      response surfaces this.
    """
    raise BobStubError(
        "Region Atlas substitution engine is reserved for Bob",
        feature="region_atlas.apply_substitutions",
        spec_doc="docs/JJSCAN_PLUS_RULES.md",
    )


def must_exist(profile: RegionProfile | None, name: str) -> RegionProfile:
    if profile is None:
        raise HeliosError(ErrorCode.REGION_NOT_FOUND, f"No region named '{name}'")
    return profile
