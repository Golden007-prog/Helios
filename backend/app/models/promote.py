"""Promote (the hero endpoint) request/response shapes — docs/API.md §5."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import ReviewState


class AutoFix(BaseModel):
    """Identifier + payload for a single auto-applied fix.

    The list of supported fix types lives in docs/JJSCAN_PLUS_RULES.md and is
    enforced by the JJSCAN+ Bob implementation.
    """

    model_config = ConfigDict(extra="allow")
    fix: str
    target: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class PromoteRequest(BaseModel):
    jcl_name: str
    source_region: str
    target_region: str
    auto_apply_fixes: list[str] = Field(default_factory=list)
    reason: str | None = None


class PromoteResponse(BaseModel):
    promote_event_id: str
    audit_event_id: str  # Same value as ``promote_event_id``; matches the
    # convention used by other state-changing endpoints (regions, scan,
    # abend) so clients can read this field uniformly.
    diff: list[dict[str, Any]]
    confidence_score: int = Field(ge=0, le=100)
    confidence_breakdown: dict[str, int | float] = Field(default_factory=dict)
    auto_fixes_applied: list[AutoFix]
    auto_fixes_available_but_not_applied: list[AutoFix] = Field(default_factory=list)
    state: ReviewState
    reviewer: str | None = None


class PromoteCancelResponse(BaseModel):
    promote_event_id: str
    state: ReviewState
