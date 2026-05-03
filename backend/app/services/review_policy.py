"""Auto-approve policy engine for the Review Queue.

Reads ``shared/config/review_queue_defaults.yaml`` and decides per audit
event whether it requires human review or is auto-approved (with the policy
that allowed it captured in the audit trail).

Decisions:

* ``auto_approve`` — no human review needed; the event still writes a
  follow-on audit row with ``actor="system:auto-approve"`` and the matching
  policy reference.
* ``review`` — initiator's request is parked in the queue; reviewer must
  decide.
* ``review_with_reason`` — same as review, but a non-empty ``reason`` is
  required on the decision.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_FILE = REPO_ROOT / "shared" / "config" / "review_queue_defaults.yaml"

Decision = Literal["auto_approve", "review", "review_with_reason"]


@dataclass(frozen=True, slots=True)
class PolicyMatch:
    decision: Decision
    matched_pattern: str
    tier: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class _Rule:
    type_pattern: str
    decision: Decision
    condition: dict[str, Any]


class ReviewPolicy:
    def __init__(self, *, policies: dict[str, list[_Rule]]) -> None:
        self._policies = policies

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "ReviewPolicy":
        path = path or DEFAULT_POLICY_FILE
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        out: dict[str, list[_Rule]] = {}
        for tier, rules in (payload.get("policies") or {}).items():
            out[tier] = [
                _Rule(
                    type_pattern=r["type"],
                    decision=r["decision"],
                    condition=r.get("condition") or {},
                )
                for r in rules
            ]
        return cls(policies=out)

    def evaluate(
        self,
        event_type: str,
        *,
        tier: str,
        confidence_score: int | None = None,
    ) -> PolicyMatch:
        """Return the first policy that matches. Falls back to a
        conservative ``review_with_reason`` if nothing matches.
        """
        for candidate_tier in (tier, "global"):
            for rule in self._policies.get(candidate_tier, []):
                if not _type_matches(event_type, rule.type_pattern):
                    continue
                if not _condition_holds(rule.condition, confidence_score=confidence_score):
                    continue
                return PolicyMatch(
                    decision=rule.decision,
                    matched_pattern=f"{candidate_tier}:{rule.type_pattern}",
                    tier=candidate_tier,
                )
        return PolicyMatch(
            decision="review_with_reason",
            matched_pattern="default-fallback",
            tier=tier,
            reason="no policy matched; safe default",
        )


def _type_matches(event_type: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(event_type, pattern)


def _condition_holds(condition: dict[str, Any], *, confidence_score: int | None) -> bool:
    if not condition:
        return True
    if "confidence_score_gte" in condition:
        if confidence_score is None:
            return False
        if confidence_score < int(condition["confidence_score_gte"]):
            return False
    return True
