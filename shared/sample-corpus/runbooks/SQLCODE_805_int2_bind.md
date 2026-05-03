# Runbook: SQLCODE -805 after promote — plan not bound in target subsystem

## Symptom
Job aborts with `SQLCODE -805` when calling stored DB2 plan/package.

## Root cause
Plan/package was not bound in the target region's collection. Common when
promoting from int2 → int3 without re-running BIND in the target subsystem.

## Fix
Run BIND in the target collection:

```
BIND PACKAGE(CUSTPKG.INT3) MEMBER(CUSTDEL) ACT(REP) ISO(CS) RELEASE(COMMIT)
```

## Verification
Run a smoke job that calls the plan. SQLCODE 0 expected.

## Prevention
The Region Atlas substitution updates the plan-collection name in the JCL
but does NOT run BIND. The Confidence Score's `db2_plan_mismatch` rule
catches this; auto-fix offers to schedule the BIND step.
