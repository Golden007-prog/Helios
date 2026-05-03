"""Learning Loop query shapes — docs/API.md §11 and docs/LEARNING_LOOP.md."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DissentResponse(BaseModel):
    rule_id: str
    region: str | None = None
    dissent_count: int
    dissent_total: int
    common_reasons: list[str] = Field(default_factory=list)


class AbendPriorEntry(BaseModel):
    cause: str
    prior_count: int
    confidence: float


class AbendPriorsResponse(BaseModel):
    abend_code: str
    program: str | None = None
    priors: list[AbendPriorEntry]


class RunbookRankEntry(BaseModel):
    runbook_id: str
    title: str
    success_count: int
    failure_count: int


class RunbookRankResponse(BaseModel):
    abend_code: str
    program: str | None = None
    runbooks: list[RunbookRankEntry]
