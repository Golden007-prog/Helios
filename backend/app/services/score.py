"""Confidence Score engine — Bob territory.

The :func:`compute` function is the formula that turns JJSCAN+ findings,
region-mismatch signals, backup-gap signals, and ABEND priors into a 0–100
score. It is the centerpiece of the Promote flow and a hero feature; Bob
owns it.

Region weights, score override events, and the weights API live next door
in :mod:`app.api.score` (real, plumbing only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.score import ScoreBreakdown


@dataclass
class ScoreContext:
    """Everything :func:`compute` may read."""

    jcl_source: str
    region_name: str
    region_weights: dict[str, int]
    findings: list[dict[str, Any]]
    backup_gap: bool
    region_mismatch_count: int
    historical_abend_priors: dict[str, int]


def compute(findings: list[dict[str, Any]], context: ScoreContext) -> tuple[int, ScoreBreakdown]:
    """Return ``(score, breakdown)`` for a candidate JCL in a target region.

    BOB: implement the scoring formula per docs/CONFIDENCE_SCORE.md.

    Required behavior (per docs/PHASE_PLAN.md §1.3 exit criteria):

    * Promoting ``CUST_DELETE_INACTIVE.JCL`` int2 → int3 with no auto-fixes
      returns score = 62.
    * Applying both auto-fixes (`generate_paired_backup`, `update_syslib`)
      returns score = 100.
    * Region weight overrides documented in docs/CONFIDENCE_SCORE.md must
      apply (e.g., int3 multiplies critical-severity deductions by 1.5).
    """
    raise NotImplementedError(
        "BOB: implement confidence score formula (docs/CONFIDENCE_SCORE.md)"
    )


def default_weights() -> dict[str, int]:
    """Default per-severity deduction weights — overridable per region.

    Kept here (not in the Bob stub) so that the weights GET endpoint can return
    something sensible before Bob lands the engine. The actual deduction math
    is :func:`compute`'s responsibility.
    """
    return {
        "critical": 25,
        "high": 10,
        "medium": 5,
        "low": 2,
        "info": 0,
    }
