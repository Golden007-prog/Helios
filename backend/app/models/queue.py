"""Review Queue request/response shapes — docs/API.md §12 and docs/REVIEW_QUEUE.md."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import ReviewState


class QueueItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    event_id: str
    type: str  # promote, region_edit, score_override, ...
    initiator: str
    ts: datetime
    state: ReviewState
    confidence_score: int | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class QueueListResponse(BaseModel):
    items: list[QueueItem]
    pending_count: int
    last_seq: str | None = None


class QueueDecisionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=400)


class QueueDecisionResponse(BaseModel):
    event_id: str
    state: ReviewState
    decided_by: str
    decided_at: datetime
    audit_event_id: str


class QueueSinceResponse(BaseModel):
    items: list[QueueItem]
    last_seq: str
