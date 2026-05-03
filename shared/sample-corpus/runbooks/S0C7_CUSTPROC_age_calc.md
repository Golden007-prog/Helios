# Runbook: S0C7 in CUSTPROC.cbl during retirement age calculation

## Symptom
S0C7 data exception at line 247, paragraph `2300-CALC-RETIREMENT`.

## Root cause
`WS-DOB` field uninitialized; reading NULL `DOB` from `CUST.MASTER` triggers
non-numeric value in `COMPUTE`.

## Fix
Add `INITIALIZE WS-DOB` at line 140, before the `MOVE`.

## Verification
Re-run job `CUST_RETIREMENT_REPORT`. No S0C7. Check spool for normal
completion of step `S020`.

## Region context
First seen: int1 (resolved 2024-03-12)
Recurrence: int2 (this incident, 2026-04-15)
Likelihood elsewhere: high — same source code is in dev1, dev2, dev3, prod
