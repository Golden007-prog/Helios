# JJSCAN+ Detection Rules

The depth feature. Every rule is a static check we run against the resolved JCL + COBOL + DB2 binding context.

Rules are tagged Phase 1 (ship for hackathon demo) or Phase 2 (roadmap, documented for credibility but not built).

---

## Rule schema

Every rule lives in `backend/services/jjscan/rules/<rule_name>.py` and exports:

```python
RULE = {
    "name": "copybook_drift",
    "severity": "high",         # critical | high | medium | low
    "phase": 1,
    "category": "consistency",
    "description": "Same copybook name resolves to different physical members",
    "matches": fn(graph, context) -> List[Finding],
    "auto_fixable": bool,
    "fix": fn(graph, finding) -> Diff,    # required if auto_fixable
}
```

Every `Finding` carries:

```python
{
    "rule": "copybook_drift",
    "severity": "high",
    "location": {"jcl": "...", "step": "...", "line": int},
    "description": "...",            # one-paragraph plain-English from Granite Code
    "explanation": "...",            # why this matters for this specific case
    "suggested_fix": "...",          # concrete change
    "auto_fixable": bool,
    "confidence": 0.0..1.0           # detection confidence
}
```

---

## Phase 1 — must demo (4 rules)

These ship for the hackathon. Every rule has a corresponding entry in the demo corpus.

### Rule 1 — `copybook_drift` (high)

**Detects:** the same copybook name resolves to different physical members across the call chain.

**Why it matters:** Two PROCs in the same job both COPY a copybook called `CUSTREC`. PROC-A's SYSLIB resolves it to `MERIDIAN.INT2.COPYLIB(CUSTREC)`, PROC-B's SYSLIB resolves it to `MERIDIAN.SHARED.COPYLIB(CUSTREC)` — same name, different fields, different lengths. Result: silent data corruption that only surfaces at runtime as an S0C7 or as wrong output.

**Algorithm:**
1. Walk the dependency graph.
2. For every COPY statement encountered, resolve to the physical member using the active SYSLIB concatenation at that point.
3. Maintain a map: `copybook_name → set[(physical_dataset, member, hash)]`.
4. Any name with more than one physical resolution → finding.

**Auto-fixable:** Yes — pin the COPY to the desired physical via explicit SYSLIB scoping or DD-level override.

### Rule 2 — `missing_proc_member` (critical)

**Detects:** `EXEC PROC=X` where X cannot be located in any concatenation.

**Why it matters:** Allocation failure, JCL won't even start. Catches the most common JCL fragility — promoting a job to a region whose PROCLIB doesn't have the expected member.

**Algorithm:**
1. For every `EXEC PROC=` (or `EXEC` of an in-stream proc), get the PROC name.
2. Resolve through the JCLLIB concatenation (or `//PROCLIB DD` override, or system PROCLIB).
3. Member not found in any → finding.

**Auto-fixable:** No — requires either copying the missing PROC to the target region's PROCLIB or adding a DD override pointing to where it lives. Helios suggests but doesn't auto-apply.

### Rule 3 — `proc_override_conflict` (high)

**Detects:** two PROCs in the chain override the same DD with conflicting values.

**Why it matters:** Subtle. The job runs but produces wrong output because PROC-A overrode `INPUT01` to `MERIDIAN.INT2.LOAD` and PROC-B (called from inside PROC-A's step) overrode it to `MERIDIAN.SHARED.LOAD`. The actual file used is determined by override-resolution rules nobody remembers.

**Algorithm:**
1. Walk the dependency graph collecting every DD override.
2. Group by `(step_name, dd_name)`.
3. Any group with more than one distinct override value → finding (with the resolved winner highlighted).

**Auto-fixable:** No — semantic decision, requires a developer.

### Rule 4 — `db2_plan_mismatch` (critical)

**Detects:** the program references a DB2 plan or package not bound in the target region's collection.

**Why it matters:** ABEND guaranteed. SQLCODE -805 within seconds of the program starting. Every shop sees this whenever a developer forgets to BIND in the target region.

**Algorithm:**
1. For every `EXEC PGM=` step that includes a `STEPLIB` containing a DB2 program, identify the program.
2. Cross-reference the bound plans/packages in the target region's `db2.collection` (queryable from Cloudant).
3. Program references plan not in collection → finding.

**Auto-fixable:** Partially — generates a `BIND PACKAGE` step suggestion. The actual BIND must be reviewed and approved.

---

## Phase 2 — roadmap (5+ rules, documented but not built)

These are listed in the README for credibility ("we know what depth looks like") and built post-hackathon.

### Rule 5 — `gdg_version_misalignment` (medium)

**Detects:** GDG referenced as `(+1)` in a step whose caller already used `(0)`.

**Why it matters:** The whole GDG generation cascade gets shifted, and downstream jobs read the wrong generation. Subtle; bug surfaces hours or days after the actual offending job ran.

### Rule 6 — `restart_step_incompatibility` (medium)

**Detects:** `RESTART=stepname` parameter pointing to a step that has `DISP=NEW` on a permanent dataset.

**Why it matters:** Restart from that step will fail allocation because the dataset already exists from the prior run. Common operator mistake during recovery.

### Rule 7 — `dead_branch` (low)

**Detects:** `COND=ONLY` after a step that always succeeds, or `COND=EVEN` on a step preceded by no possible failure path.

**Why it matters:** Cosmetic, indicates code rot. Often points to features removed without cleaning up the JCL.

### Rule 8 — `circular_includes` (high)

**Detects:** `INCLUDE MEMBER=X` chain where X eventually includes itself.

**Why it matters:** JCL parser explodes or hangs. JES rejects the job with a confusing error.

### Rule 9 — `missing_syslib_member` (critical)

**Detects:** A program that COPY-includes a member not present in any SYSLIB concatenation entry.

**Why it matters:** Compile-time failure (in COBOL). Or runtime failure if dynamic. Catches the case where someone forgot to migrate a copybook alongside the program.

### Rule 10 — `dataset_size_mismatch` (medium)

**Detects:** `SPACE=(CYL,(N,M))` where N+M is significantly smaller than the historical maximum size of the dataset for similar jobs.

**Why it matters:** D37 (out of space) ABEND. Predictable from history.

### Rule 11 — `expired_dataset_reference` (low)

**Detects:** Job references a dataset whose retention period has expired and which is scheduled for deletion.

**Why it matters:** Job will fail next month when the dataset is gone. Early warning.

### Rule 12 — `pds_member_collision` (medium)

**Detects:** Two parallel jobs in the same scheduler queue both write to the same PDS member.

**Why it matters:** Last-writer-wins; one job's output is silently lost.

---

## Detection rule scoring

When a JJSCAN+ scan completes, findings are aggregated and weighted:

```
total_penalty = Σ (finding.severity_weight × finding.confidence)
```

Default severity weights (overridable per region):
- `critical`: 25
- `high`: 10
- `medium`: 5
- `low`: 2

The total penalty subtracts from the Confidence Score baseline of 100. Full formula in [`CONFIDENCE_SCORE.md`](CONFIDENCE_SCORE.md).

---

## "Explain this finding" — Granite Code integration

Each finding's `description` and `explanation` fields are generated by Granite Code 8B. Prompt template lives in `shared/prompts/jjscan_explain.txt`:

```
You are a senior z/OS mainframe engineer reviewing a JCL dependency finding.

Rule: {rule_name}
Location: {location}
Raw context: {ast_excerpt}

In two paragraphs, explain to a junior developer:
1. What this finding means in plain English (no jargon-heavy answer).
2. Why it matters for THIS specific job — name the dataset, the program, and the
   concrete failure mode that would result if not fixed.

Be specific. If you don't know enough to be specific, say so and suggest what
information would be needed.
```

Temperature 0.2 for consistency. Cached per `(rule, location_hash)` in Cloudant for 24h.

---

## Rule lifecycle

When a rule is added:

1. Implement in `backend/services/jjscan/rules/<rule_name>.py`
2. Add unit tests in `backend/services/jjscan/rules/<rule_name>_test.py`
3. Seed an example trigger in the MeridianBank corpus
4. Document in this file
5. Update [`SPECS.md`](SPECS.md) detection rules table
6. PR review confirms all five steps before merge

When a rule is deprecated:

1. Mark `phase: 0` in the RULE dict
2. Logger at WARN level any time the rule fires
3. Document the deprecation in this file under "Deprecated rules"
4. After 30 days of zero firings, remove

---

## Learning loop

Every finding the team **dismisses** writes to Cloudant `helios_learning` with:
- The full finding payload
- Who dismissed it
- Why (free-text — required)
- Job characteristics for similarity matching

When a similar finding fires later, the UI surfaces:

> *"3 of 4 prior teams dismissed this finding as false positive on similar jobs. Their reasons: [collapsible list]."*

Doesn't auto-suppress — that would defeat the rule. Just informs.

This is the "AI agent that gets smarter" angle. Implementation in `backend/services/jjscan/learning.py`. Surfaces via the same API as findings.

---

## Why we ship 4 rules instead of 9

Hackathon scope discipline. Four well-detected rules with strong demo cases beat nine half-built rules where two miss-fire and embarrass us in front of judges.

The roadmap section above signals depth without overcommitting. When a judge asks "what about CICS, what about IMS?" we point to this doc.
