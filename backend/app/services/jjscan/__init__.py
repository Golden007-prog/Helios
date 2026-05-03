"""JJSCAN+ rule framework.

The framework + harness are real (so Bob can drop in rules and tests pass).
The four seeded rules — JJ-COPYBOOK-DRIFT-001, JJ-MISSING-PROC-MEMBER-001,
JJ-PROC-OVERRIDE-CONFLICT-001, JJ-DB2-PLAN-MISMATCH-001 — are stubbed.
"""

from app.services.jjscan.framework import (
    Rule,
    RuleContext,
    RuleResult,
    RuleSeverity,
    Scanner,
)

__all__ = ["Rule", "RuleContext", "RuleResult", "RuleSeverity", "Scanner"]
