"""JJSCAN+ rule framework.

* ``Rule`` — base class. Subclasses set ``rule_id`` + ``severity`` and
  implement :meth:`Rule.run`.
* ``RuleContext`` — what each rule sees: source text, region profile,
  Cloudant + watsonx clients (for the rules that need them).
* ``RuleResult`` — what each rule returns. The scanner converts these into
  ``Finding`` documents for ``helios_findings``.
* ``Scanner`` — runs the registered rules in order, captures durations,
  and returns the aggregate.

The rule *framework* is plumbing — that's here. The four seeded rules are
Bob territory and live in ``app.services.jjscan.rules``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from app.models.common import Severity, Subject

if TYPE_CHECKING:
    from app.models.region import RegionProfile
    from app.services.cloudant import CloudantClient
    from app.services.watsonx import WatsonxClient


# Re-exported for convenience — same enum, different name to keep rule code
# readable (`severity=RuleSeverity.MEDIUM`).
RuleSeverity = Severity


@dataclass
class RuleContext:
    """Everything a rule may read."""

    jcl_source: str
    target_region: "RegionProfile | None"
    region_name: str | None
    jcl_name: str | None
    cloudant: "CloudantClient | None"
    watsonx: "WatsonxClient | None"


@dataclass
class RuleResult:
    """A single finding produced by a rule."""

    rule_id: str
    severity: RuleSeverity
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    auto_fix_available: bool = False


class Rule:
    """Base class for JJSCAN+ rules.

    Subclasses set ``rule_id`` and ``severity`` as class vars and implement
    :meth:`run`. ``run`` returns a list (zero or more findings).
    """

    rule_id: ClassVar[str] = "JJ-BASE-000"
    severity: ClassVar[RuleSeverity] = RuleSeverity.LOW
    description: ClassVar[str] = "Base rule — never instantiate directly"

    def run(self, ctx: RuleContext) -> list[RuleResult]:  # pragma: no cover - abstract
        raise NotImplementedError(
            f"BOB: rule {self.rule_id} must implement Rule.run (see docs/JJSCAN_PLUS_RULES.md)"
        )


class Scanner:
    """Runs a set of rules over a single JCL source."""

    def __init__(self, rules: list[Rule]) -> None:
        self._rules = rules

    @property
    def rule_ids(self) -> list[str]:
        return [r.rule_id for r in self._rules]

    def scan(self, ctx: RuleContext) -> tuple[list[RuleResult], int]:
        """Run every rule. Returns (results, total_duration_ms)."""
        started = time.perf_counter()
        out: list[RuleResult] = []
        for rule in self._rules:
            try:
                out.extend(rule.run(ctx))
            except NotImplementedError:
                # Re-raise so the API contract test can see the BOB marker
                # at the rule layer, not just the scanner layer.
                raise
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return out, elapsed_ms


def build_finding_subject(ctx: RuleContext) -> Subject:
    return Subject(
        kind="jcl",
        name=ctx.jcl_name or "<inline>",
        region=ctx.region_name,
    )
