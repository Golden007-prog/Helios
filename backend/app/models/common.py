"""Cross-feature primitives.

These types appear in many request/response models, so they live in one place
to keep TS codegen tidy.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeatureName(str, Enum):
    """Helios feature pillars — used for tagging audit events and metrics."""

    REGION_ATLAS = "region_atlas"
    JJSCAN_PLUS = "jjscan_plus"
    ABEND_ARCHAEOLOGIST = "abend_archaeologist"
    CONFIDENCE_SCORE = "confidence_score"
    REVIEW_QUEUE = "review_queue"
    AUDIT_LOG = "audit_log"
    LEARNING_LOOP = "learning_loop"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewState(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class FindingState(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    SUPERSEDED = "superseded"


class RegionTier(str, Enum):
    DEVELOPMENT = "development"
    INTEGRATION = "integration"
    QA = "qa"
    UAT = "uat"
    PRODUCTION = "production"


class StubMarker(BaseModel):
    """Returned in ``error.details`` for every Bob-stub 501.

    Tests assert this shape so the BOB worklist stays discoverable.
    """

    model_config = ConfigDict(extra="forbid")
    feature: str
    spec: str | None = None
    reserved_for: str = Field(default="Bob (audit-trail-bearing AI)")


class Subject(BaseModel):
    """Minimal pointer to an artifact (used in audit + finding documents)."""

    kind: str
    name: str
    region: str | None = None


class TimestampedDoc(BaseModel):
    """Mixin for any doc persisted in Cloudant — see docs/DATA_MODEL.md §2."""

    schema_version: str = Field(default="1.0")
    kind: str
    ts: datetime
    ts_unix_ms: int
    shop: str = Field(default="meridianbank")


def merge_extra(base: dict[str, Any], extra: dict[str, Any] | None) -> dict[str, Any]:
    """Helper used by request adapters that pass through unknown fields."""
    if not extra:
        return base
    return {**base, **extra}
