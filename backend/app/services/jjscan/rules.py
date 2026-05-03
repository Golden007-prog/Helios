"""The four seeded JJSCAN+ rules — Bob territory.

Per docs/PHASE_PLAN.md §1.3 and docs/JJSCAN_PLUS_RULES.md, these four rules
power the Confidence Score 62 → 100 transition that is the centerpiece of the
demo. Each :meth:`Rule.run` raises ``NotImplementedError`` with a one-line
spec; Bob fills them in.

The framework + tests around the rules are real — when Bob drops in any
rule's body, the contract tests start passing without code changes elsewhere.
"""

from __future__ import annotations

from app.services.jjscan.framework import Rule, RuleContext, RuleResult, RuleSeverity


class CopybookDriftRule(Rule):
    """JJ-COPYBOOK-DRIFT-001 — copybook version mismatch between source + target SYSLIB chain.

    BOB: parse all COPY statements, resolve each through ``ctx.target_region``'s
    SYSLIB chain (Cloudant ``helios_jcl_artifacts`` joined with the region's
    SYSLIB DSNs), compare resolved versions to source, raise medium-severity
    findings on mismatch with auto-fix available (rewrite SYSLIB DD).
    """

    rule_id = "JJ-COPYBOOK-DRIFT-001"
    severity = RuleSeverity.MEDIUM
    description = "Copybook resolves to a different version in target region's SYSLIB chain"

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        raise NotImplementedError(
            "BOB: implement copybook drift rule (docs/JJSCAN_PLUS_RULES.md § JJ-COPYBOOK-DRIFT-001)"
        )


class MissingProcMemberRule(Rule):
    """JJ-MISSING-PROC-MEMBER-001 — JCLLIB references a proc not present in any concatenated PDS.

    BOB: walk JCLLIB DD, then every EXEC PROC=, then resolve the proc member
    against the JCLLIB chain. Missing → high severity; auto-fix unavailable.
    """

    rule_id = "JJ-MISSING-PROC-MEMBER-001"
    severity = RuleSeverity.HIGH
    description = "Referenced PROC member is not present in any JCLLIB concatenation"

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        raise NotImplementedError(
            "BOB: implement missing PROC member rule "
            "(docs/JJSCAN_PLUS_RULES.md § JJ-MISSING-PROC-MEMBER-001)"
        )


class ProcOverrideConflictRule(Rule):
    """JJ-PROC-OVERRIDE-CONFLICT-001 — step-level override conflicts with PROC defaults.

    BOB: parse PROC defaults, compare against step EXEC overrides, raise
    medium severity on conflicts that change destructive behavior (e.g., DISP
    OLD vs SHR on a protected dataset).
    """

    rule_id = "JJ-PROC-OVERRIDE-CONFLICT-001"
    severity = RuleSeverity.MEDIUM
    description = "Step override conflicts with PROC default in a destructive way"

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        raise NotImplementedError(
            "BOB: implement PROC override conflict rule "
            "(docs/JJSCAN_PLUS_RULES.md § JJ-PROC-OVERRIDE-CONFLICT-001)"
        )


class Db2PlanMismatchRule(Rule):
    """JJ-DB2-PLAN-MISMATCH-001 — DB2 plan collection in JCL doesn't match target region.

    BOB: extract DB2 plan and collection from RUN PROGRAM(IKJEFT01) /
    DSN SYSTEM SUBSYS lines; compare against ``ctx.target_region.db2``;
    raise critical on mismatch with auto-fix that rewrites the SUBSYS line.
    """

    rule_id = "JJ-DB2-PLAN-MISMATCH-001"
    severity = RuleSeverity.CRITICAL
    description = "DB2 plan/collection in JCL does not match target region configuration"

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        raise NotImplementedError(
            "BOB: implement DB2 plan mismatch rule "
            "(docs/JJSCAN_PLUS_RULES.md § JJ-DB2-PLAN-MISMATCH-001)"
        )


SEEDED_RULES: list[Rule] = [
    CopybookDriftRule(),
    MissingProcMemberRule(),
    ProcOverrideConflictRule(),
    Db2PlanMismatchRule(),
]
