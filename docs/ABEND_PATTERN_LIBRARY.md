# ABEND Pattern Library

The ABEND Archaeologist ships with 15 pre-seeded patterns covering the most common production failures across COBOL/JCL/DB2/VSAM. This is what makes the "AI explains your dump" feature work for any reasonable input on demo day, not just the one we happened to test.

Patterns live in Cloudant `abend_patterns` collection, seeded on first backend startup from `shared/sample-corpus/abend_patterns/`.

---

## Pattern schema

```yaml
code: "S0C7"
class: "data_exception"
language_scope: ["cobol"]
regex_signatures:
  - "S0C7"
  - "DATA EXCEPTION"
  - "ABEND CODE 0C7"
typical_causes:
  - "Numeric operation on non-numeric data"
  - "Uninitialized COMP-3 field"
  - "DISPLAY value used where numeric expected"
  - "Bad input record with non-numeric where numeric expected"
investigation_steps:
  - "Identify the failing instruction address from the dump"
  - "Map address to source line via the compile listing or ProLeap parser"
  - "Walk MOVE chains backward from the failing field"
  - "Inspect the input record format — DCB, RECFM, LRECL"
  - "Check for missing INITIALIZE on WORKING-STORAGE numerics"
common_fixes:
  - "Add INITIALIZE statement before first use of the numeric field"
  - "Add NUMERIC test before arithmetic: IF WS-FIELD IS NUMERIC THEN..."
  - "Validate input record at READ; reject non-conforming with proper logging"
related_findings:
  - "uninitialized_numeric_field"
  - "display_to_comp_assignment"
related_runbooks:
  - "rb-cobol-s0c7-handling"
seeded_examples:
  - dump_file: "shared/sample-corpus/abend_examples/s0c7_custproc.txt"
    failing_program: "CUSTPROC"
    failing_paragraph: "2300-CALC-RETIREMENT"
    failing_field: "WS-CUST-AGE"
    notes: "DOB read as NULL, MOVE'd to WS-DOB without initialization"
```

---

## The 15 seeded patterns

### COBOL runtime ABENDs (5)

#### 1. `S0C7` — Data exception

The flagship demo pattern. Numeric op on non-numeric. The ABEND every COBOL developer has debugged at 3am.

#### 2. `S0C4` — Protection exception

Memory access violation. Common causes: subscript out of range on OCCURS table, REDEFINES mismatch, addressability lost on a passed parameter.

#### 3. `S322` — Time exceeded

Job ran past its TIME= limit. Usually a runaway loop, infinite EVALUATE fallthrough, or a query against an unindexed table that's grown 10x.

#### 4. `U4038` — LE user abend

Language Environment unhandled exception. Often a wrapper around something more specific (S0C7 inside, surfaced as U4038 because LE intercepted).

#### 5. `IGZ0035S` — COBOL paragraph not found

PERFORM target paragraph misspelled or removed. Compile-time should catch it but dynamic CALLs can hit this at runtime.

### JCL / allocation ABENDs (5)

#### 6. `S806` — Program not found

Missing STEPLIB / JOBLIB, wrong program name, link-edit failure. The first ABEND a developer sees after a botched promotion.

#### 7. `S813` — Wrong volume

Tape mount mismatch, dataset not cataloged in the target region. Catches the case where someone migrated the dataset definition but not the catalog entry.

#### 8. `IEC141I 013-18` — I/O error, member not found in PDS

The "did you forget to add the member to the PROCLIB" error. Common after promotion.

#### 9. `IEF272I` — Step not executed (allocation failure)

Volume full, dataset name conflict, RACF authority denied. The dump usually has the actual reason in a preceding `IEF233I` or `IGD17xxx` message.

#### 10. `IEC031I D37` — Out of space

Primary + secondary extents exhausted. Predictable from history (Rule 10 in the JJSCAN+ roadmap).

#### 11. `IEC150I` — Open failed

Catalog mismatch, dataset state wrong (e.g., GDG model missing), DD parameter conflict.

### DB2 ABENDs (4)

#### 12. `SQLCODE -805` — Plan not bound

Program references plan/package not present in target subsystem's collection. The most common DB2 promotion failure.

#### 13. `SQLCODE -811` — Multi-row result

`SELECT INTO` returned more than one row without a cursor. Either the data changed (new duplicate rows) or the predicate is too loose.

#### 14. `SQLCODE -904` — Resource unavailable

Tablespace stopped, lock contention, utility running on the table. Often transient — retry succeeds.

#### 15. `SQLCODE -922` — Authorization failure

RACF / DB2 GRANT mismatch. Common when promoting a job to a region whose RACF user doesn't have the same DB2 grants as the source.

---

## Pattern matching algorithm

When a dump is pasted in:

1. **Tokenize** the dump text into JES message lines, abend code lines, dump address lines.
2. **For each pattern**, run all `regex_signatures` against the tokenized lines. Score by:
   - Number of matching signatures (more = stronger)
   - Position of matches (earlier in dump = stronger)
   - Token-similarity to historical resolved incidents in `helios_learning` for this region
3. **Rank patterns** by composite score. Top match's confidence = score / theoretical_max.
4. If top confidence > 0.7, present as primary diagnosis.
5. If top confidence 0.4–0.7, present as "likely" with the runner-up as alternative.
6. If top confidence < 0.4, present as "unable to confidently match" — fall back to letting Granite Code attempt cold analysis on the raw dump.

---

## COBOL traceback (S0C7 deep dive)

When the failing program is in our corpus or accessible via the helios-corpus MCP:

1. Identify failing instruction address from dump (`PSW=`, `INSTRUCTION ADDRESS=`)
2. Locate the compile listing (or rebuild a synthetic one via ProLeap parser on the source)
3. Map address → source line
4. Identify the failing field (the operand of the failing instruction)
5. Walk MOVE chains backward:
   - Find every `MOVE ... TO <failing_field>` in the program
   - For each source field, recursively trace its origin
   - Stop at READ statements (input from outside) or INITIALIZE statements (known good state)
6. Build the `data_trace` list returned in the API response

Example trace for the demo:

```
WS-CUST-AGE
  ← computed from WS-DOB at line 247 (paragraph 2300-CALC-RETIREMENT)
WS-DOB
  ← MOVE'd from CUSTREC.DOB at line 142 (paragraph 1000-PROCESS-RECORD)
CUSTREC.DOB
  ← READ from MERIDIAN.CUST.MASTER at line 95 (paragraph 0500-READ-INPUT)
```

Granite Code converts this trace + the surrounding paragraph code into a plain-English business-rule explanation.

---

## Seeded example dumps

`shared/sample-corpus/abend_examples/` contains one example dump file per pattern, named like `s0c7_custproc.txt`, `iec141i_013_18_proclib.txt`, `sqlcode_-805_meridplA.txt`. Each is a realistic-looking JES/SYSLOG/CEEDUMP excerpt produced from the corpus programs.

These ensure the demo always has a working detection regardless of what the judge pastes in (in the worst case, we paste the seeded sample ourselves and the demo proceeds).

---

## Cross-region context

For any matched pattern, the API also returns:

```json
"similar_prior_incidents": [
  {
    "date": "2024-03-12",
    "region": "int1",
    "program": "CUSTPROC",
    "resolution": "Initialized WS-DOB to spaces before MOVE; resolved by adding INITIALIZE statement at line 140.",
    "resolved_by": "sarah"
  }
]
```

These come from the team's `runbooks` Cloudant collection. When the team saves a new ABEND resolution, it's stored here with `region`, `pattern_id`, `resolution`, `resolved_by`, indexed by `(pattern_id, region)`.

This is the "democratize the ABEND oracle" play. Every senior dev's painful past becomes future juniors' pre-loaded knowledge.

---

## Runbook generation

After a successful diagnosis, the user can click "Save runbook" to create a reusable entry:

```markdown
# Runbook: S0C7 in CUSTPROC.cbl during retirement age calculation

## Symptom
S0C7 data exception at line 247, paragraph 2300-CALC-RETIREMENT

## Root cause
WS-DOB field uninitialized; reading NULL DOB from CUST.MASTER triggers
non-numeric value in COMPUTE.

## Fix
Add INITIALIZE WS-DOB at line 140, before the MOVE.

## Verification
Re-run job CUST_RETIREMENT_REPORT. No S0C7. Check spool for normal
completion of step S020.

## Region context
First seen: int1 (resolved by sarah, 2024-03-12)
Recurrence: int2 (this incident, 2026-04-15)
Likelihood elsewhere: high — same source code is in dev1, dev2, dev3, prod
```

The runbook is saved to `helios_runbooks` collection, indexed for retrieval next time anyone hits a related abend.

---

## Pattern coverage measurement

We measure pattern library coverage as: `% of seeded test dumps the library correctly identifies with confidence > 0.7`.

Current target for hackathon submission: **15 of 15 patterns at confidence ≥ 0.85** on their respective seeded test dumps. (Easy because we control the test data — but the discipline of hitting it forces clean regex signatures.)

For real-world data: target 70%+ correct identification on a held-out sample of 100 anonymized real ABEND dumps. Out of hackathon scope but documented as success criterion for v1.0 GA.

---

## Adding new patterns post-hackathon

1. Create `shared/sample-corpus/abend_patterns/<code>.yaml` following the schema above
2. Create a seeded example dump in `shared/sample-corpus/abend_examples/<code>_<scenario>.txt`
3. Run the seed script — pattern is auto-loaded into Cloudant on next backend restart
4. Add a row to this doc's "15 seeded patterns" table

No code changes required. The matching engine reads from Cloudant.
