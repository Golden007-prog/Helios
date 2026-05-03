"""Audit log query shapes — docs/API.md §10 and docs/AUDIT_LOG.md."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditChain(BaseModel):
    prev_event_id: str | None = None
    prev_event_hash: str | None = None
    this_event_hash: str


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(alias="_id")
    type: str
    actor: str
    actor_role: str
    ts: datetime
    ts_unix_ms: int
    subject: dict[str, Any]
    before_sha256: str | None = None
    after_sha256: str | None = None
    result: str
    error: str | None = None
    client_meta: dict[str, Any] = Field(default_factory=dict)
    chain: AuditChain


class AuditQueryResponse(BaseModel):
    events: list[AuditEvent]
    bookmark: str | None = None


class AuditBundleRequest(BaseModel):
    subject_kind: str | None = None
    subject_name: str | None = None
    subject_region: str | None = None
    actor: str | None = None
    type: str | None = None
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None


class AuditBundleResponse(BaseModel):
    bundle_job_id: str


class AuditBundleStatusResponse(BaseModel):
    bundle_job_id: str
    state: str  # pending | running | completed | failed
    download_url: str | None = None
    error: str | None = None


class AttestationResponse(BaseModel):
    date: str
    chain_root_hash: str
    event_count: int
