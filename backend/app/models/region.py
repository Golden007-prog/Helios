"""Region Atlas request/response shapes — see docs/REGION_PROFILE_SCHEMA.md."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import RegionTier


class Db2Config(BaseModel):
    subsystem_id: str
    plan_collection: str
    default_bind: dict[str, str] = Field(default_factory=dict)


class JesConfig(BaseModel):
    class_: str = Field(alias="class")
    sysout_class: str
    model_config = ConfigDict(populate_by_name=True)


class ReviewConfig(BaseModel):
    auto_approve_threshold: int = Field(default=90, ge=0, le=100)
    allowed_reviewers: dict[str, list[str]] = Field(default_factory=dict)


class RegionProfile(BaseModel):
    """Full region document — keeps shape in sync with docs/DATA_MODEL.md §3."""

    model_config = ConfigDict(extra="allow")
    name: str
    tier: RegionTier
    hlq: str
    db2: Db2Config | None = None
    racf_group: str | None = None
    jes: JesConfig | None = None
    scheduler_queue: str | None = None
    volser_pattern: str | None = None
    gdg_retention: int | None = None
    protected_resources: list[str] = Field(default_factory=list)
    confidence_weight_overrides: dict[str, int] = Field(default_factory=dict)
    review: ReviewConfig = Field(default_factory=ReviewConfig)


class RegionListItem(BaseModel):
    name: str
    tier: RegionTier
    hlq: str


class RegionListResponse(BaseModel):
    regions: list[RegionListItem]
    total: int


class DiffField(BaseModel):
    path: str
    a: Any | None = None
    b: Any | None = None
    kind: str  # value_change | added | removed


class RegionDiffResponse(BaseModel):
    a: str
    b: str
    fields: list[DiffField]


class RegionUpsertRequest(BaseModel):
    profile: RegionProfile
    reason: str = Field(min_length=3, max_length=400)


class RegionUpsertResponse(BaseModel):
    name: str
    audit_event_id: str
    review_required: bool


class RegionForkRequest(BaseModel):
    overrides: dict[str, Any]
    reason: str = Field(min_length=3, max_length=400)


class RegionForkResponse(BaseModel):
    region: str
    job_name: str
    audit_event_id: str
