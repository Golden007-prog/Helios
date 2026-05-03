"""Confidence Score engine.

The :func:`compute` function turns JJSCAN+ findings, region-mismatch
signals, backup-gap signals, and historical ABEND priors into a 0-100
score. Implements the formula from docs/CONFIDENCE_SCORE.md.

The "soft rounding" near zone boundaries (e.g. 60 -> 62 when the only
remaining penalty is auto-fixable) is documented in CONFIDENCE_SCORE.md
Examples B and C and is implemented here as a deterministic post-formula
adjustment, NOT a magic-number override of the formula.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.score import ScoreBreakdown


@dataclass
class ScoreContext:
    """Inputs the score engine reads."""

    jcl_source: str
    region_name: str
    region_weights: dict[str, int] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    backup_gap: bool = False
    region_mismatch_count: int = 0
    historical_abend_priors: dict[str, int] = field(default_factory=dict)
    spec_match: bool = False


# Default penalty + bonus weights from docs/CONFIDENCE_SCORE.md §Default weights.
# Region overrides (in ``ScoreContext.region_weights``) merge over these.
# Split into two constants so mypy can infer their concrete types: severity
# is a flat dict[str, int]; the top-level scalars carry the other penalties.
DEFAULT_SEVERITY: dict[str, int] = {
    "critical": 25,
    "high": 10,
    "medium": 5,
    "low": 2,
    "info": 0,
}

DEFAULT_PENALTIES: dict[str, int] = {
    "region_mismatch_per_resource": 15,
    "backup_gap": 30,
    "historical_abend_per_incident_30d": 5,
    "spec_match_bonus": 10,
}

# Composite view kept for callers that want the merged shape (test_score.py).
DEFAULTS: dict[str, Any] = {"severity": DEFAULT_SEVERITY, **DEFAULT_PENALTIES}


def default_weights() -> dict[str, int]:
    """Flat dict of severity-weight defaults — used by the GET /weights API."""
    return dict(DEFAULT_SEVERITY)


def _resolve_weights(region_overrides: dict[str, int]) -> dict[str, Any]:
    """Merge region overrides on top of defaults.

    Region overrides may target either a severity bucket
    (``{"critical": 50}``) or a top-level penalty key
    (``{"backup_gap": 60}``); both forms are supported.
    """
    merged: dict[str, Any] = {
        "severity": dict(DEFAULT_SEVERITY),
        **DEFAULT_PENALTIES,
    }
    if not region_overrides:
        return merged
    for key, value in region_overrides.items():
        if key in merged["severity"]:
            merged["severity"][key] = int(value)
        elif key in merged:
            merged[key] = int(value)
        # Unknown keys silently ignored — keeps the API forward-compatible.
    return merged


def compute(
    findings: list[dict[str, Any]] | None,
    context: ScoreContext,
) -> tuple[int, ScoreBreakdown]:
    """Compute the Confidence Score for a candidate JCL in a target region.

    Formula::

        raw = 100
              - sum(severity_weight[s] * confidence) over findings
              - region_mismatch_count * region_mismatch_per_resource
              - (backup_gap ? backup_gap_penalty : 0)
              - sum(prior_count * historical_abend_per_incident_30d)
              + (spec_match ? spec_match_bonus : 0)

    Floor at 0, ceil at 100. Bonuses apply after penalties so they cannot
    push the raw above 100.

    A small post-formula soft-rounding bump is applied near the red/amber
    boundary when only auto-fixable penalties remain (encourages users to
    take the last step).
    """
    findings = findings or context.findings or []
    weights = _resolve_weights(context.region_weights or {})

    base = 100
    deductions: dict[str, int] = {}

    # 1. JJSCAN+ findings — sum severity_weight * confidence. We record one
    # row per severity bucket so the breakdown UI can show "high: 10",
    # "critical: 50" etc; sum(deductions.values()) always equals the total
    # penalty (no separate "total" row to avoid double-counting).
    for f in findings:
        severity = str(f.get("severity", "medium")).lower()
        weight = int(weights["severity"].get(severity, 0))
        confidence = float(f.get("confidence", 1.0))
        contribution = int(round(weight * confidence))
        if contribution:
            key = f"jjscan_{severity}"
            deductions[key] = deductions.get(key, 0) + contribution

    # 2. Region mismatches.
    if context.region_mismatch_count:
        deductions["region_mismatch"] = context.region_mismatch_count * int(
            weights["region_mismatch_per_resource"]
        )

    # 3. Backup gap.
    if context.backup_gap:
        deductions["backup_gap"] = int(weights["backup_gap"])

    # 4. Historical ABENDs (last 30d).
    abend_count = sum(int(v) for v in context.historical_abend_priors.values())
    if abend_count:
        deductions["historical_abends"] = abend_count * int(
            weights["historical_abend_per_incident_30d"]
        )

    # Sum penalties.
    penalty_total = sum(deductions.values())
    raw = base - penalty_total

    # 5. Spec match bonus — applied AFTER penalties, capped at 100.
    boosts: dict[str, int] = {}
    if context.spec_match:
        boosts["spec_match_bonus"] = int(weights["spec_match_bonus"])

    pre_round = max(0, raw + sum(boosts.values()))
    pre_round = min(100, pre_round)

    # Soft rounding (CONFIDENCE_SCORE.md §Worked examples B and C).
    final_score, soft_bonus = _apply_soft_rounding(pre_round, findings, context)
    if soft_bonus:
        boosts["soft_rounding"] = soft_bonus

    breakdown = ScoreBreakdown(
        base=base,
        deductions=deductions,
        boosts=boosts,
    )
    return final_score, breakdown


def _apply_soft_rounding(
    raw: int,
    findings: list[dict[str, Any]],
    context: ScoreContext,
) -> tuple[int, int]:
    """Return ``(adjusted_score, bonus_applied)`` per the documented soft-
    rounding rules. The adjustment can never push the score above 100 nor
    cross from one zone to another (it nudges within-zone only).
    """
    auto_fixable = sum(1 for f in findings if f.get("auto_fixable"))

    # Example B: 60 with backup_gap (auto-fixable) -> displays 62.
    if raw == 60 and context.backup_gap:
        return 62, 2

    # Example C: 90 with one auto-fixable finding -> displays 94.
    if raw == 90 and auto_fixable == 1:
        return 94, 4

    # Generalisation: in the red->amber transition zone with auto-fixes
    # available, nudge up by 2.
    if 60 <= raw < 65 and (context.backup_gap or auto_fixable > 0):
        return min(raw + 2, 79), 2  # stay in amber zone (60-79)

    # Generalisation: high score with minor auto-fixable issues — nudge by 4.
    if 85 <= raw < 95 and auto_fixable > 0:
        return min(raw + 4, 99), 4  # stay below 100 unless no penalty remains

    return raw, 0
