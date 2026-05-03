"""Confidence Score request/response shapes — docs/API.md §7 and docs/CONFIDENCE_SCORE.md."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScoreBreakdown(BaseModel):
    """Per-component contribution to the final score.

    The exact set of keys is owned by the Bob implementation of
    `app.services.score.compute`; this model is open-ended so the frontend
    can render whatever the engine produces.
    """

    model_config = ConfigDict(extra="allow")
    base: int = 100
    deductions: dict[str, int] = Field(default_factory=dict)
    boosts: dict[str, int] = Field(default_factory=dict)


class ScoreRequest(BaseModel):
    jcl_source: str | None = None
    jcl_name: str | None = None
    region: str

    @model_validator(mode="after")
    def _one_form(self) -> ScoreRequest:
        if (self.jcl_source is None) == (self.jcl_name is None):
            raise ValueError("provide exactly one of jcl_source or jcl_name")
        return self


class ScoreResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    breakdown: ScoreBreakdown


class WeightsResponse(BaseModel):
    region: str
    weights: dict[str, int]
    source: str  # "default" | "override" | "merged"


class WeightsUpdateRequest(BaseModel):
    weights: dict[str, int]
    reason: str = Field(min_length=3, max_length=400)


class WeightsUpdateResponse(BaseModel):
    region: str
    weights: dict[str, int]
    audit_event_id: str
    review_required: bool


class ScoreOverrideRequest(BaseModel):
    new_score: int = Field(ge=0, le=100)
    reason: str = Field(min_length=3, max_length=400)


class ScoreOverrideResponse(BaseModel):
    event_id: str
    original_score: int
    new_score: int
    audit_event_id: str
    learning_event_id: str
