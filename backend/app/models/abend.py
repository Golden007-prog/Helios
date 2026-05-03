"""ABEND Archaeologist request/response shapes — docs/API.md §8."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AbendTier(str, Enum):
    """Confidence tiers for ABEND classification — docs/ABEND_PATTERN_LIBRARY.md."""

    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNFAMILIAR = "unfamiliar"
    UNKNOWN = "unknown"


class AbendContext(BaseModel):
    region: str
    job_name: str
    occurred_at: datetime | None = None


class AbendRequest(BaseModel):
    raw_text: str = Field(min_length=1)
    context: AbendContext


class IdentifiedAbend(BaseModel):
    code: str
    message_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    tier: AbendTier


class FailingStep(BaseModel):
    step_name: str | None = None
    program: str | None = None
    offset_hex: str | None = None


class SourceTrace(BaseModel):
    file: str | None = None
    line: int | None = None
    paragraph: str | None = None
    highlighted_field: str | None = None


class RankedRootCause(BaseModel):
    cause: str
    prior_count: int
    confidence: float = Field(ge=0.0, le=1.0)


class MatchingRunbook(BaseModel):
    id: str
    title: str
    success_count: int


class AbendResponse(BaseModel):
    """Full ABEND analysis envelope. ``degraded`` carries the unfamiliar-tier flow."""

    model_config = ConfigDict(extra="allow")
    identified_abend: IdentifiedAbend
    failing_step: FailingStep
    source_trace: SourceTrace
    business_rule_explanation: str
    ranked_root_causes: list[RankedRootCause]
    matching_runbooks: list[MatchingRunbook]
    degraded: bool = False
    degraded_reason: str | None = None


class AbendResolveRequest(BaseModel):
    root_cause_choice: str
    applied_runbook_id: str | None = None
    outcome: str  # resolved | did_not_resolve
    notes: str | None = None


class AbendResolveResponse(BaseModel):
    event_id: str
    audit_event_id: str
    learning_event_id: str
