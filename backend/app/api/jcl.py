"""JCL artifact routes — docs/API.md §4.

These are pure plumbing on top of Cloudant; no Bob-stub logic in this module.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.dependencies import CurrentUser, get_audit_writer, get_cloudant, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import ErrorCode, HeliosError
from app.models.jcl import (
    JCLArtifact,
    JCLHistoryEntry,
    JCLHistoryResponse,
    JCLListItem,
    JCLListResponse,
    JCLState,
    JCLUpsertRequest,
    JCLUpsertResponse,
)
from app.services.audit_writer import AuditWriter
from app.services.cloudant import CloudantClient

router = APIRouter()


@router.get("", response_model=Envelope[JCLListResponse])
async def list_jcl(
    user: CurrentUser,
    region: str = Query(...),
    state: JCLState | None = Query(default=None),
    score_lt: int | None = Query(default=None, ge=0, le=100),
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[JCLListResponse]:
    selector: dict = {
        "shop": settings.shop,
        "kind": "jcl_artifact",
        "region": region,
    }
    if state:
        selector["state"] = state.value
    if score_lt is not None:
        selector["current_confidence_score"] = {"$lt": score_lt}
    result = await cloudant.find("jcl_artifacts", selector, limit=200)
    items = [
        JCLListItem(
            name=d["name"],
            region=d["region"],
            state=d["state"],
            current_confidence_score=d.get("current_confidence_score"),
        )
        for d in result.get("docs", [])
    ]
    return ok(JCLListResponse(artifacts=items, total=len(items)))


async def _load_jcl(cloudant: CloudantClient, region: str, name: str, shop: str) -> dict:
    result = await cloudant.find(
        "jcl_artifacts",
        {"shop": shop, "kind": "jcl_artifact", "region": region, "name": name},
        limit=1,
    )
    docs = result.get("docs", [])
    if not docs:
        raise HeliosError(
            ErrorCode.JCL_NOT_FOUND,
            f"No JCL '{name}' in region '{region}'",
        )
    return docs[0]


@router.get("/{region}/{name}", response_model=Envelope[JCLArtifact])
async def get_jcl(
    region: str,
    name: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> Envelope[JCLArtifact]:
    doc = await _load_jcl(cloudant, region, name, settings.shop)
    for k in ("_id", "_rev", "kind", "schema_version", "shop"):
        doc.pop(k, None)
    return ok(JCLArtifact.model_validate(doc))


@router.get("/{region}/{name}/source", response_class=PlainTextResponse)
async def get_jcl_source(
    region: str,
    name: str,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    settings=Depends(get_settings_dep),
) -> PlainTextResponse:
    doc = await _load_jcl(cloudant, region, name, settings.shop)
    source = doc.get("source", "")
    return PlainTextResponse(content=source, media_type="text/plain")


@router.post("/{region}/{name}", response_model=Envelope[JCLUpsertResponse])
async def upsert_jcl(
    region: str,
    name: str,
    body: JCLUpsertRequest,
    user: CurrentUser,
    cloudant: CloudantClient = Depends(get_cloudant),
    audit: AuditWriter = Depends(get_audit_writer),
    settings=Depends(get_settings_dep),
) -> Envelope[JCLUpsertResponse]:
    sha = hashlib.sha256(body.source.encode("utf-8")).hexdigest()
    new_doc: dict = {
        "kind": "jcl_artifact",
        "schema_version": "1.0",
        "shop": settings.shop,
        "name": name,
        "region": region,
        "state": JCLState.DRAFT.value,
        "source": body.source,
        "source_blob_sha256": sha,
        "source_blob_ref": f"blob:{region}/{name}@{sha[:8]}",
        "open_findings_count": 0,
    }
    try:
        existing = await _load_jcl(cloudant, region, name, settings.shop)
        new_doc["_id"] = existing["_id"]
        new_doc["_rev"] = existing.get("_rev")
        before = existing
    except HeliosError:
        before = None
    stored = await cloudant.put("jcl_artifacts", new_doc)
    event = await audit.write_event(
        type="jcl_edit",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "jcl", "name": name, "region": region},
        before=before,
        after=stored,
        extra={"reason": body.reason},
    )
    return ok(
        JCLUpsertResponse(
            name=name,
            region=region,
            source_blob_sha256=sha,
            audit_event_id=event["_id"],
            state=JCLState.DRAFT,
        )
    )


@router.get("/{region}/{name}/history", response_model=Envelope[JCLHistoryResponse])
async def jcl_history(
    region: str,
    name: str,
    user: CurrentUser,
    audit: AuditWriter = Depends(get_audit_writer),
) -> Envelope[JCLHistoryResponse]:
    result = await audit.query(subject_kind="jcl", subject_name=name, limit=200)
    entries = [
        JCLHistoryEntry(
            event_id=e["_id"],
            type=e["type"],
            actor=e["actor"],
            ts=e["ts"],
        )
        for e in result.get("docs", [])
        if e.get("subject", {}).get("region") == region
    ]
    return ok(JCLHistoryResponse(artifact=name, region=region, events=entries))
