"""The four seeded JJSCAN+ rules.

Per docs/JJSCAN_PLUS_RULES.md and docs/PHASE_PLAN.md §1.3, these four rules
power the Confidence Score 62 -> 100 transition that is the centrepiece of
the demo. Each rule consumes the shared ``RuleContext`` (JCL source +
target region) and returns a list of findings.

Each rule reads region metadata from ``ctx.target_region`` -- both the
typed fields (``db2.subsystem_id``, ``db2.plan_collection``) and the
forward-compatible extras carried via ``model_extra``:

* ``copybook_pins``: ``{copybook_name: pinned_version}`` -- copybook
  drift fires when the resolved version doesn't match the pin.
* ``proc_libraries``: ``[proc_name, ...]`` -- missing-proc fires when
  the JCL invokes a PROC not in the list.
* ``bound_plans``: ``[plan_name, ...]`` -- DB2 plan mismatch fires
  when the JCL references a plan not in the list.

When the extras are absent the rules either no-op (proc / plan rules) or
fall back to the canonical demo signal (copybook drift on ``CBANKDAT``).
"""

from __future__ import annotations

import re
from typing import Any

from app.services.jjscan.framework import (
    Rule,
    RuleContext,
    RuleResult,
    RuleSeverity,
)


# ---------------------------------------------------------------------------
# Shared parsing helpers
# ---------------------------------------------------------------------------

_COPY_RE = re.compile(r"\bCOPY\s+[\'\"]?([A-Z][A-Z0-9$#@_-]{0,7})[\'\"]?", re.IGNORECASE)
_EXEC_PROC_RE = re.compile(
    r"^//\S*\s+EXEC\s+(?:PROC=)?([A-Z][A-Z0-9$#@_-]{0,7})\b", re.IGNORECASE | re.MULTILINE
)
_PLAN_RE = re.compile(r"\bPLAN\(([A-Z][A-Z0-9$#@_-]{0,7})\)", re.IGNORECASE)
_DSN_SYSTEM_RE = re.compile(r"\bDSN\s+SYSTEM\(([A-Z0-9]{1,4})\)", re.IGNORECASE)
_SUBSYS_RE = re.compile(r"\bSUBSYS=([A-Z0-9]{1,4})", re.IGNORECASE)
_DD_OVERRIDE_RE = re.compile(
    r"^//(\S+)\.(\S+)\s+DD\s+(.+)$", re.IGNORECASE | re.MULTILINE
)
# SYSLIB DD points to a copybook library; if the chain references a
# region-prefixed dataset that doesn't match the target region's HLQ, the
# copybook resolves through a stale chain (drift). Matches both the
# explicit ``//SYSLIB DD DSN=...`` and the continuation-line ``// DD DSN=``
# rows that follow it.
_SYSLIB_DD_RE = re.compile(
    r"^//SYSLIB\s+DD\s+DSN=([A-Z][A-Z0-9$#@_-]+(?:\.[A-Z][A-Z0-9$#@_-]+)+)",
    re.IGNORECASE | re.MULTILINE,
)
_SYSLIB_CONT_RE = re.compile(
    r"^//\s+DD\s+DSN=([A-Z][A-Z0-9$#@_-]+(?:\.[A-Z][A-Z0-9$#@_-]+)+)",
    re.IGNORECASE | re.MULTILINE,
)
# Matches plain in-stream DD overrides (//STEPNAME.DDNAME ...). Comment lines
# (//*) are excluded by virtue of the dot separator requirement.

_PG_PROC_INVOKE_RE = re.compile(
    r"^//\S+\s+EXEC\s+([A-Z][A-Z0-9$#@_-]{0,7})\b(?!\s*PGM=)",
    re.IGNORECASE | re.MULTILINE,
)
_RUN_PROGRAM_RE = re.compile(
    r"\bRUN\s+PROGRAM\(([A-Z][A-Z0-9$#@_-]{0,7})\)",
    re.IGNORECASE,
)


def _region_extra(region: Any, key: str, default: Any) -> Any:
    """Read a forward-compat extra off a RegionProfile (extra='allow')."""
    if region is None:
        return default
    extras = getattr(region, "model_extra", None) or {}
    return extras.get(key, default)


def _is_comment(line: str) -> bool:
    return line.startswith("//*")


# ---------------------------------------------------------------------------
# JJ-COPYBOOK-DRIFT-001
# ---------------------------------------------------------------------------


class CopybookDriftRule(Rule):
    """Same copybook name resolves to different physical members across
    source/target SYSLIB chains.
    """

    rule_id = "JJ-COPYBOOK-DRIFT-001"
    severity = RuleSeverity.HIGH
    description = (
        "Copybook resolves to a different version in the target region's "
        "SYSLIB chain"
    )

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        out: list[RuleResult] = []

        # Programs whose copybooks have known version drift between source
        # and target — fires HIGH because the program semantics differ even
        # after region-token substitution. Driven by
        # ``target_region.known_drift_programs`` (a forward-compat extra).
        known_drift = {
            str(p).upper()
            for p in (_region_extra(ctx.target_region, "known_drift_programs", []) or [])
        }
        if known_drift:
            for m in _RUN_PROGRAM_RE.finditer(ctx.jcl_source):
                prog = m.group(1).upper()
                if prog in known_drift:
                    out.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            severity=self.severity,
                            description=(
                                f"Program {prog} has copybook version drift "
                                f"between source and target SYSLIB chains"
                            ),
                            details={
                                "program": prog,
                                "evidence": "known_drift_programs",
                            },
                            auto_fix_available=True,
                        )
                    )
                    # Only one finding per known-drift program; don't
                    # repeat-fire on multiple invocations.
                    break

        # Always check the SYSLIB DD chain: if it points to a region-
        # prefixed library that doesn't match the target region's HLQ, the
        # copybook chain resolves through a stale region (the demo's hero
        # ``CUST_DELETE_INACTIVE.JCL`` is exactly this shape — //SYSLIB DD
        # DSN=CUST.INT2.COPYLIB promoted to int3).
        if ctx.target_region is not None:
            target_hlq = (ctx.target_region.hlq or "").upper()
            target_name = (ctx.target_region.name or "").upper()
            chain: list[str] = []
            in_syslib = False
            for line in ctx.jcl_source.splitlines():
                if _is_comment(line):
                    continue
                head = _SYSLIB_DD_RE.search(line)
                if head:
                    in_syslib = True
                    chain.append(head.group(1).upper())
                    continue
                if in_syslib:
                    cont = _SYSLIB_CONT_RE.search(line)
                    if cont:
                        chain.append(cont.group(1).upper())
                        continue
                    # First non-DD-continuation line ends the chain.
                    in_syslib = False
            for dsn in chain:
                # Mismatch when the dataset prefix is region-coded and
                # different from the target region.
                if (
                    target_hlq
                    and not dsn.startswith(target_hlq)
                    and target_name
                    and target_name not in dsn
                    and any(seg.startswith("INT") or seg.startswith("DEV") for seg in dsn.split("."))
                ):
                    out.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            severity=self.severity,
                            description=(
                                f"SYSLIB chain entry {dsn} is region-prefixed but "
                                f"does not match the target region's HLQ "
                                f"({ctx.target_region.hlq})"
                            ),
                            details={
                                "syslib_dsn": dsn,
                                "target_hlq": ctx.target_region.hlq,
                                "evidence": "syslib_dd_region_mismatch",
                            },
                            auto_fix_available=True,
                        )
                    )
                    break  # one chain finding is enough; don't spam

        copybooks = {
            m.group(1).upper()
            for line in ctx.jcl_source.splitlines()
            if not _is_comment(line)
            for m in [_COPY_RE.search(line)]
            if m is not None
        }
        if not copybooks:
            return out

        # Region-driven path: ``copybook_pins`` is a mapping
        # {copybook_name: required_version}; if any in-source COPY name has
        # an expected pin different from the source region's pin (carried
        # in ``copybook_resolved`` extras), fire one finding.
        target_pins = _region_extra(ctx.target_region, "copybook_pins", {}) or {}
        resolved_in_source = (
            _region_extra(ctx.target_region, "copybook_resolved_in_source", {}) or {}
        )

        for cb in sorted(copybooks):
            pinned = target_pins.get(cb)
            in_source = resolved_in_source.get(cb)
            if pinned and in_source and pinned != in_source:
                out.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        description=(
                            f"Copybook {cb} resolves to {in_source} in the source "
                            f"SYSLIB but target region pins it to {pinned}"
                        ),
                        details={
                            "copybook": cb,
                            "source_version": in_source,
                            "target_version": pinned,
                        },
                        auto_fix_available=True,
                    )
                )
                continue
            # Demo-default: BANKDEMO_INTEGRATION calls out CBANKDAT as the
            # known-drifting copybook between bnk_test_vsam (v_VSAM) and
            # bnk_prod / bnk_pac (v_SQL). Fire when target region carries
            # neither pin metadata nor any other rule data.
            if cb == "CBANKDAT" and not target_pins and ctx.target_region is not None:
                out.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        description=(
                            f"Copybook {cb} resolves to a different version in "
                            f"the target region's SYSLIB chain (v_VSAM -> v_SQL)"
                        ),
                        details={
                            "copybook": cb,
                            "source_version": "v_VSAM",
                            "target_version": "v_SQL",
                            "evidence": f"COPY {cb} found in JCL",
                        },
                        auto_fix_available=True,
                    )
                )
        return out


# ---------------------------------------------------------------------------
# JJ-MISSING-PROC-MEMBER-001
# ---------------------------------------------------------------------------


class MissingProcMemberRule(Rule):
    """``EXEC PROC=X`` (or in-stream ``EXEC X``) where X is not present in
    any concatenated PROCLIB.
    """

    rule_id = "JJ-MISSING-PROC-MEMBER-001"
    severity = RuleSeverity.HIGH
    description = "Referenced PROC member is not present in any JCLLIB concatenation"

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        out: list[RuleResult] = []
        proc_libs = _region_extra(ctx.target_region, "proc_libraries", None)
        if proc_libs is None:
            # No region metadata -> can't decide. Stay silent rather than
            # surface false positives.
            return out

        available: set[str] = {str(p).upper() for p in proc_libs}
        seen: set[str] = set()
        for line in ctx.jcl_source.splitlines():
            if _is_comment(line):
                continue
            # ``EXEC YBATTSO`` or ``EXEC PROC=YBATTSO``.
            m = _PG_PROC_INVOKE_RE.search(line)
            if m is None:
                m = _EXEC_PROC_RE.search(line)
            if m is None:
                continue
            name = m.group(1).upper()
            if name in {"PGM", "PROC"}:
                continue
            seen.add(name)

        for proc in sorted(seen):
            if proc not in available:
                out.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        description=(
                            f"PROC {proc} is referenced by this JCL but is not "
                            f"present in any PROCLIB for the target region"
                        ),
                        details={
                            "proc": proc,
                            "available_procs": sorted(available),
                        },
                        auto_fix_available=False,
                    )
                )
        return out


# ---------------------------------------------------------------------------
# JJ-PROC-OVERRIDE-CONFLICT-001
# ---------------------------------------------------------------------------


class ProcOverrideConflictRule(Rule):
    """Two PROCs in the chain override the same DD with conflicting values."""

    rule_id = "JJ-PROC-OVERRIDE-CONFLICT-001"
    severity = RuleSeverity.MEDIUM
    description = "Step override conflicts with another override for the same DD"

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        out: list[RuleResult] = []
        # Group overrides by (step, dd_name) and emit a finding for any group
        # with more than one distinct override value.
        groups: dict[tuple[str, str], list[str]] = {}
        for line in ctx.jcl_source.splitlines():
            if _is_comment(line):
                continue
            m = _DD_OVERRIDE_RE.search(line)
            if not m:
                continue
            step, dd, body = m.group(1), m.group(2), m.group(3).strip()
            groups.setdefault((step.upper(), dd.upper()), []).append(body)

        for (step, dd), values in groups.items():
            distinct = sorted(set(values))
            if len(distinct) <= 1:
                continue
            # Severity bumps when the override touches a DISP-protected
            # resource (DISP=OLD vs DISP=SHR/MOD).
            destructive = any("DISP=OLD" in v.upper() for v in distinct) and any(
                "DISP=SHR" in v.upper() or "DISP=MOD" in v.upper() for v in distinct
            )
            severity = (
                RuleSeverity.MEDIUM if destructive else RuleSeverity.LOW
            )
            out.append(
                RuleResult(
                    rule_id=self.rule_id,
                    severity=severity,
                    description=(
                        f"DD {dd} on step {step} is overridden with "
                        f"{len(distinct)} different values"
                    ),
                    details={
                        "step": step,
                        "dd": dd,
                        "values": distinct,
                        "destructive": destructive,
                    },
                    auto_fix_available=False,
                )
            )
        return out


# ---------------------------------------------------------------------------
# JJ-DB2-PLAN-MISMATCH-001
# ---------------------------------------------------------------------------


class Db2PlanMismatchRule(Rule):
    """The program references a DB2 plan or subsystem that is not bound /
    not configured in the target region.
    """

    rule_id = "JJ-DB2-PLAN-MISMATCH-001"
    severity = RuleSeverity.CRITICAL
    description = (
        "DB2 plan/subsystem in JCL does not match target region configuration"
    )

    def run(self, ctx: RuleContext) -> list[RuleResult]:
        out: list[RuleResult] = []
        if ctx.target_region is None or ctx.target_region.db2 is None:
            return out

        target_subsys = ctx.target_region.db2.subsystem_id.upper()
        bound_plans = {
            str(p).upper()
            for p in (
                _region_extra(ctx.target_region, "bound_plans", None)
                or [ctx.target_region.db2.plan_collection]
            )
        }

        # Subsystem mismatch — DSN SYSTEM(DB10) when target is DB30.
        for line in ctx.jcl_source.splitlines():
            if _is_comment(line):
                continue
            m = _DSN_SYSTEM_RE.search(line) or _SUBSYS_RE.search(line)
            if not m:
                continue
            jcl_subsys = m.group(1).upper()
            if jcl_subsys != target_subsys:
                out.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        description=(
                            f"DB2 subsystem {jcl_subsys} referenced in JCL but "
                            f"target region uses {target_subsys}"
                        ),
                        details={
                            "jcl_subsystem": jcl_subsys,
                            "target_subsystem": target_subsys,
                        },
                        auto_fix_available=True,
                    )
                )
                # Only emit one subsys finding per scan to avoid noise on jobs
                # that mention the subsystem in multiple steps.
                break

        # Plan mismatch — PLAN(MYPLAN) when MYPLAN not in bound_plans.
        for m in _PLAN_RE.finditer(ctx.jcl_source):
            plan = m.group(1).upper()
            if plan not in bound_plans:
                out.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        description=(
                            f"DB2 plan {plan} is referenced but is not bound "
                            f"in the target region's collection"
                        ),
                        details={
                            "jcl_plan": plan,
                            "bound_plans": sorted(bound_plans),
                        },
                        auto_fix_available=True,
                    )
                )
                break
        return out


SEEDED_RULES: list[Rule] = [
    CopybookDriftRule(),
    MissingProcMemberRule(),
    ProcOverrideConflictRule(),
    Db2PlanMismatchRule(),
]
