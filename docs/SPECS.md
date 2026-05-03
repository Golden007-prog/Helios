# Specifications

Feature-by-feature contracts. If implementation deviates from this doc, update the doc — don't drift.

---

## Feature 1 — Region Atlas

### Purpose

Encode per-region tribal knowledge as a versioned artifact. Make promotion between regions a one-click operation with auditable substitutions.

### Region profile schema (YAML)

Each region lives in `shared/sample-corpus/regions/<region-name>.yaml`:

```yaml
region: int3
description: "Integration test environment 3 — used for pre-prod release validation"
hlq:
  application: "MERIDIAN.INT3"
  test_data: "MERIDIAN.INT3.TEST"
  backup: "MERIDIAN.INT3.BAK"
db2:
  subsystem: "DBI3"
  collection: "MERIDIAN_INT3"
  default_plan: "MERIDPL3"
  bind_options:
    isolation: "CS"
    acquire: "USE"
    release: "COMMIT"
    validate: "BIND"
    qualifier: "MERINT3"
racf:
  user_default: "MERINT3"
  groups:
    - "MERIDDEV"
    - "MERIDBATCH"
jes:
  class: "C"
  msgclass: "X"
  notify: "MERIDOPS"
scheduler:
  queue: "INT3_BATCH"
  default_priority: 5
volser:
  primary: "INT3*"
  backup: "BAK3*"
jobcard_template: |
  //${JOBNAME} JOB (${ACCT}),'${PROGRAMMER}',
  //         CLASS=${jes.class},
  //         MSGCLASS=${jes.msgclass},
  //         NOTIFY=${jes.notify}
sysout_class: "X"
restart_strategy: "step"
```

### Operations

**`GET /regions`** — list all known regions
**`GET /regions/{name}`** — fetch one profile
**`PUT /regions/{name}`** — upsert (writes `audit_log` entry with diff)
**`POST /regions/{a}/diff/{b}`** — structured diff with reasoning
**`POST /promote`** — input: `{jcl, source_region, target_region}`. Output: `{rewritten_jcl, substitutions: [{path, from, to, reason}], backup_required: [resources]}`

### Promote-job logic

1. Parse the source JCL into an AST.
2. Walk the AST. For every node whose value matches a known field in the source region's profile, mark it as a substitution candidate.
3. For each candidate, look up the target region's value. If different, record the substitution with a one-sentence reason ("changed `DSN SYSTEM(DBI2)` to `DSN SYSTEM(DBI3)` because target region uses int3 subsystem").
4. Detect protected resources in the JCL (DELETE, UPDATE, INSERT against tracked DB2 tables; DISP=OLD on tracked VSAM clusters). Add to `backup_required`.
5. Return the rewritten JCL + substitution list + backup requirements.

### Pre-flight backup generator

Triggered when `backup_required` is non-empty. For each protected resource:

- **DB2 table:** generate a paired job step containing `UNLOAD` (DSNUTILB) followed by `IMAGE COPY`, with target dataset `${target_region.hlq.backup}.<table>.D<yyyyddd>.T<hhmmss>`, retention 30 days.
- **VSAM cluster:** generate `IDCAMS REPRO` with output cluster `${target_region.hlq.backup}.<cluster>.D<yyyyddd>`.

Backup job is presented to the user as a separate JCL the user can accept or skip. If accepted, it's prepended as the first step in the promotion package.

### Region edit UI (Sayan)

Two-pane Monaco editor. Left: source YAML. Right: validated preview with field types and inline help. Save commits to Cloudant via the API and writes an `audit_log` entry.

### Diff view (the demo hero shot)

Side-by-side YAML render. Differences highlighted with three colors (added green / removed red / modified yellow). Hover reveals the reasoning the rewrite engine would apply if you promoted in this direction. Targeted for at least 8 seconds of demo screen time — make it pretty.

---

## Feature 2 — JJSCAN+

### Purpose

Resolve every dependency a JCL touches across SYSLIB concatenation order. Catch the static failures `jjscan` won't.

### Resolver algorithm

1. Parse JCL into AST.
2. Build the SYSLIB resolution order from STEPLIB, JOBLIB, system libraries (in that order).
3. For each `EXEC PROC=`, locate the PROC member; recurse into it.
4. For each `INCLUDE MEMBER=`, locate and inline.
5. For each COPY statement in COBOL programs invoked via `EXEC PGM=`, locate the copybook member.
6. Build the full call graph as a directed graph: nodes are JCL / PROC / COPYBOOK / PGM / DD / DSN / PLAN; edges carry concatenation context.

### Detection rules (Phase 1 — must demo)

| Rule | Severity | What it catches |
|---|---|---|
| `copybook_drift` | High | Same copybook name resolving to different physical members across the call chain |
| `missing_proc_member` | Critical | `EXEC PROC=X` where X is not in any concatenation |
| `proc_override_conflict` | High | Two PROCs in the chain override the same DD with conflicting values |
| `db2_plan_mismatch` | Critical | Program references plan/package not present in target region's collection |

### Detection rules (Phase 2 — roadmap, not built for hackathon demo)

`gdg_version_misalignment`, `restart_step_incompatibility`, `dead_branch`, `circular_includes`, `missing_syslib_member`. Listed in the README so judges see depth without us overcommitting.

### Output

```json
{
  "graph": { "nodes": [...], "edges": [...] },
  "findings": [
    {
      "rule": "copybook_drift",
      "severity": "high",
      "location": { "jcl": "CUST_DELETE_INACTIVE.JCL", "step": "S010", "line": 47 },
      "description": "Copybook CUSTREC resolves to MERIDIAN.INT2.COPYLIB(CUSTREC) here but MERIDIAN.INT3.COPYLIB(CUSTREC) in the target region",
      "explanation": "<one-paragraph plain-English explanation generated by Granite Code>",
      "suggested_fix": "<concrete change to the JCL or a recommendation to align copybook versions>",
      "auto_fixable": true
    }
  ]
}
```

### "Explain this PROC" button

In the dependency graph, click any node → side panel opens with a Granite Code summary of what that PROC / COPYBOOK / PGM does. Caches per Cloudant entry to avoid re-burning Bobcoins.

---

## Feature 3 — ABEND Archaeologist

### Purpose

Turn the on-call developer's 4am ABEND triage from a 4-hour archaeological dig into a 4-minute guided diagnosis.

### Input

User pastes one or more of: SYSLOG / JESYSMSG / JESJCL / CEEDUMP / SVC dump / SYSOUT excerpt. No size limit on the UI; backend chunks if needed.

### Pre-seeded pattern library

Cloudant collection `abend_patterns` ships with ~15 entries covering the most common production failures:

| Code | Class | Typical cause |
|---|---|---|
| `S0C7` | Data exception | Numeric op on non-numeric (uninitialized field, bad input record, DISPLAY for COMP-3) |
| `S0C4` | Protection exception | Subscript out of range, OCCURS table overflow, redefines mismatch |
| `S322` | Time exceeded | Runaway loop, infinite EVALUATE fallthrough |
| `S806` | Program not found | Missing STEPLIB / JOBLIB, wrong program name, link-edit failure |
| `S813` | Wrong volume | Tape mount mismatch, dataset not cataloged in target region |
| `U4038` | LE user abend | COBOL exception not handled by language environment |
| `SQLCODE -805` | Plan not bound | Program references plan not bound to subsystem |
| `SQLCODE -811` | Multi-row | SELECT INTO returned > 1 row without FETCH cursor |
| `SQLCODE -904` | Resource unavailable | Tablespace stopped, lock contention, utility running |
| `SQLCODE -922` | Authorization failure | RACF / DB2 GRANT mismatch |
| `IEC141I 013-18` | I/O error | Member not found in PDS |
| `IEF272I` | Step not executed | Allocation failure, SPACE exhaustion |
| `IEC031I D37` | Out of space | Primary + secondary extents exhausted |
| `IEC150I` | Open failed | Catalog mismatch, dataset state wrong |
| `IGZ0035S` | COBOL paragraph not found | PERFORM target paragraph misspelled or removed |

Each entry stores: regex pattern, typical cause, three concrete fix recipes, related copybook fields to inspect, related runbook IDs.

### Triage flow

1. Pattern-match the dump against the library. Score each match by regex confidence × token-similarity to historical resolved incidents.
2. For top match: extract the failing program name, step, DD, dataset.
3. If the failing program is in our corpus (or accessible via MCP corpus server), parse it. Locate the failing instruction.
4. Trace back through MOVE chains, PERFORM call sites, and parameter passing to find the data origin.
5. Use Granite Code to produce a plain-English explanation of the business rule that broke ("This field is set in paragraph 2300-CALC-RETIREMENT, derived from DOB read from CUST.MASTER. The non-numeric value came from row INSERTed 2024-03-12 with DOB=NULL").
6. Cross-reference the team's prior resolutions for similar abends in this region.
7. Generate a runbook entry the user can save back to the team's library.

### Output

```json
{
  "abend_code": "S0C7",
  "confidence": 0.94,
  "failing_step": "S020",
  "failing_program": "CUSTPROC",
  "failing_paragraph": "2300-CALC-RETIREMENT",
  "failing_field": "WS-CUST-AGE",
  "data_trace": [
    {"step": "MOVE", "from": "CUSTREC.DOB", "to": "WS-DOB", "line": 142},
    {"step": "COMPUTE", "expr": "WS-CUST-AGE = CURRENT-DATE - WS-DOB", "line": 247}
  ],
  "business_explanation": "<plain English from Granite Code>",
  "similar_prior_incidents": [
    {"date": "2024-03-12", "region": "int1", "resolution": "Initialized WS-DOB to spaces before MOVE; resolved by adding INITIALIZE statement at line 140."}
  ],
  "suggested_fix": "<concrete COBOL diff>",
  "runbook_draft": "<markdown ready to save>"
}
```

---

## Feature 4 — Confidence Score (the wrapper)

### Purpose

One number every reviewer trusts. Replaces "looks fine to me" review culture with auditable risk arithmetic.

### Formula

```
score = 100
      − Σ(jjscan_findings × severity_weight)
      − region_mismatch_penalty
      − backup_gap_penalty
      − historical_abend_penalty
      + spec_match_bonus
```

Default weights (configurable per region in `regions/<name>.yaml` under `confidence_weights`):

| Component | Weight |
|---|---|
| `severity.critical` | 25 |
| `severity.high` | 10 |
| `severity.medium` | 5 |
| `severity.low` | 2 |
| `region_mismatch_per_resource` | 15 |
| `backup_gap` (when protected resource untouched) | 30 |
| `historical_abend_per_incident_30d` | 5 |
| `spec_match_bonus` | +10 (capped at 100 total) |

Score floor is 0, ceiling is 100.

Full rules and override mechanism in [`CONFIDENCE_SCORE.md`](CONFIDENCE_SCORE.md).

### UI

Big SVG gauge. Traffic light: red 0–59, amber 60–79, green 80–100. Below the gauge: top 3 reasons the score is not 100, each with a "fix" button when auto-fixable. Clicking "fix all auto-fixable" applies suggested changes and shows a diff before commit.

This is the demo hero shot — give it the most polish.

### Override

A reviewer can override the score (e.g., "we accept this risk for this one promotion"). Override requires a written reason; the override + reason is appended to `audit_log` and surfaced on the PR.

---

## Feature 5 — Audit Log (cross-cutting)

Every state-changing action writes an immutable entry to Cloudant `audit_log`:

```json
{
  "_id": "auto-generated",
  "timestamp": "2026-05-02T15:34:12Z",
  "actor": "golden",
  "action": "region.update",
  "target": "int3",
  "before": { "<full region YAML before>" },
  "after": { "<full region YAML after>" },
  "diff": [ {"path": "...", "from": "...", "to": "..."} ],
  "reason": "user-supplied (required for overrides)",
  "helios_version": "0.1.0"
}
```

UI tab: filterable, exportable to CSV. SOX/compliance-ready from day one.

---

## Feature 6 — Review Queue (cross-cutting)

When Maya promotes a job, Raj sees a real-time toast. Implementation:

1. Promote endpoint writes a `queue` entry to Cloudant.
2. Backend WebSocket hub subscribes to Cloudant `_changes` feed filtered to `queue`.
3. Connected clients (other team members' browsers) get a push.
4. Reviewer clicks the toast → opens the diff + score → approves or requests changes.

Demo this with a split screen on judging day. Two-developer hackathon team becomes the unfair advantage.

---

## Out of scope (intentionally)

- Real LPAR connection. We use the synthetic MeridianBank corpus and parse JCL/COBOL statically. No SSH to z/OS, no FTP, no SMP/E.
- Live ABEND ingestion from a running mainframe. We accept pasted dumps only.
- Code generation (RPG/COBOL → Java/Python). Listed as a roadmap item; not built for the hackathon.
- AI governance / bias evaluation of the inference layer. Listed as roadmap.
