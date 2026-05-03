"""JCL artifact request/response shapes — see docs/DATA_MODEL.md §6."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class JCLState(str, Enum):
    DRAFT = "draft"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class PromotedFrom(BaseModel):
    region: str
    blob_sha256: str
    promote_event_id: str


class JCLArtifact(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    region: str
    state: JCLState
    source_blob_sha256: str
    source_blob_ref: str | None = None
    promoted_from: PromotedFrom | None = None
    current_confidence_score: int | None = Field(default=None, ge=0, le=100)
    current_confidence_breakdown: dict[str, int | float] = Field(default_factory=dict)
    open_findings_count: int = 0
    last_modified_event_id: str | None = None


class JCLListItem(BaseModel):
    name: str
    region: str
    state: JCLState
    current_confidence_score: int | None = None


class JCLListResponse(BaseModel):
    artifacts: list[JCLListItem]
    total: int


class JCLUpsertRequest(BaseModel):
    source: str = Field(min_length=1)
    reason: str = Field(min_length=3, max_length=400)


class JCLUpsertResponse(BaseModel):
    name: str
    region: str
    source_blob_sha256: str
    audit_event_id: str
    state: JCLState


class JCLHistoryEntry(BaseModel):
    event_id: str
    type: str
    actor: str
    ts: datetime


class JCLHistoryResponse(BaseModel):
    artifact: str
    region: str
    events: list[JCLHistoryEntry]
