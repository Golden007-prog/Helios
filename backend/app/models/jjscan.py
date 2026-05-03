"""JJSCAN+ request/response shapes — docs/API.md §6 and docs/JJSCAN_PLUS_RULES.md."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.common import FindingState, Severity, Subject


class ScanRequest(BaseModel):
    """Either ``jcl_source`` (inline) or ``jcl_name`` + ``region`` (named)."""

    model_config = ConfigDict(extra="forbid")
    jcl_source: str | None = None
    jcl_name: str | None = None
    region: str | None = None
    target_region: str | None = None

    @model_validator(mode="after")
    def _one_form(self) -> ScanRequest:
        has_inline = self.jcl_source is not None
        has_named = self.jcl_name is not None and self.region is not None
        if has_inline == has_named:
            raise ValueError("provide either jcl_source OR (jcl_name + region), not both")
        return self


class Finding(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    rule_id: str
    severity: Severity
    description: str
    details: dict[str, Any] = Field(default_factory=dict)
    subject: Subject
    state: FindingState = FindingState.OPEN
    auto_fix_available: bool = False
    dissent_count: int | None = None
    dissent_total: int | None = None
    common_dismiss_reasons: list[str] = Field(default_factory=list)


class ScanResponse(BaseModel):
    findings: list[Finding]
    scan_duration_ms: int = 0


class FindingDecideRequest(BaseModel):
    decision: FindingState  # accept | dismiss
    reason: str = Field(min_length=3, max_length=400)
    reason_tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _legal(self) -> FindingDecideRequest:
        if self.decision not in {FindingState.ACCEPTED, FindingState.DISMISSED}:
            raise ValueError("decision must be 'accepted' or 'dismissed'")
        return self


class FindingDecideResponse(BaseModel):
    finding_id: str
    state: FindingState
    decided_at: datetime
    audit_event_id: str
    learning_event_id: str


class FindingAutoFixResponse(BaseModel):
    finding_id: str
    fix_applied: str
    new_score: int | None = None
    audit_event_id: str
