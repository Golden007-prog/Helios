# Bob session — land Scene 1 + Scene 2 hero stubs

**Branch:** `feat/1.3-scene-1-and-2-stubs`
**Owner:** Golden
**Mode plan:** Plan → confirm → Code → Plan-review export
**Estimated coin burn:** medium — one focused session, ~3-4 work hours of typing
**Spec doc anchor:** `docs/PHASE_PLAN.md` §1.2, §1.3, §1.4

---

## Why this session

The backend currently boots, the audit writer + Cloudant + Review Queue + chain
verifier all work, and the seed corpus is in place. But every hero endpoint
returns 501 because the inference / scoring / diff bodies are still stubs. We
cannot run a Scene 1 demo (`62 → 94 → 100` Promote) or a Scene 2 demo (S0C7
ABEND triage) end-to-end. The `make demo-smoke` and `make abend-smoke` targets
xfail on every meaningful step.

This session is the smallest set of bodies that turns those xfails green. After
this lands, deploy can proceed (Code Engine + GitHub Pages), and both demo
scenes work against the live URLs.

Out of scope for this session: Promote auto-fix loop on the *substituted* JCL
(the `update_syslib` rewrite happens but only emits a finding-fix trace; the
score recompute uses the canned post-fix value), the runbook editor, the
learning-loop dissent recompute. Those are next session.

---

## Resolved ambiguities (read these BEFORE Plan mode)

A planning-pass review surfaced three under-specified things in the v1 prompt.
Resolutions are pinned here so Code mode doesn't burn coins guessing.

### R1 — Diff scope is a fixed allowlist, NOT a leaf walk

Walking every leaf between `bnk_test_vsam` and `bnk_prod` produces ~21
differences (tier, protected_resources, confidence weight overrides, storage
backend, proclibs, copylibs, db2_bound_plans, etc). The "exactly 7" contract
in the test is **not** a claim that the YAMLs are byte-equal except for 7
fields — that would force unrealistic seeds (a prod region SHOULD have
stricter weights and a different storage backend).

Instead: define a single source of truth at the top of
`app/services/region_atlas.py`:

```python
SUBSTITUTION_SURFACE: tuple[str, ...] = (
    "hlq",
    "db2.subsystem_id",
    "db2.plan_collection",
    "racf_group",
    "jes.class",
    "scheduler_queue",
    "volser_pattern",
)
```

`diff_regions` walks ONLY these paths. `apply_substitutions` rewrites the JCL
along these same paths. One constant, two consumers. Adding a new
substitution later means appending to `SUBSTITUTION_SURFACE` and nothing
else.

Verified against current YAMLs — **no seed fix needed**:

| # | Path | int2 → int3 | bnk_test_vsam → bnk_prod |
|---|---|---|---|
| 1 | `hlq` | `CUST.INT2` → `CUST.INT3` | `MFI01T.MFIDEMO` → `MFI01.MFIDEMO` |
| 2 | `db2.subsystem_id` | `DBI2` → `DBI3` | `DB10` → `DB30` |
| 3 | `db2.plan_collection` | `CUSTPKG.INT2` → `CUSTPKG.INT3` | `MFIDEMO_T` → `MFIDEMO_P` |
| 4 | `racf_group` | `INT2DEV` → `INT3DEV` | `BNKDEV` → `BNKPROD` |
| 5 | `jes.class` | `A` → `P` | `T` → `P` |
| 6 | `scheduler_queue` | `BATCH_DEV` → `BATCH_INT` | `BATCH_TEST` → `BATCH_PROD` |
| 7 | `volser_pattern` | `INT2*` → `INT3*` | `TST*` → `PRD*` |

All 7 differ in both pairs, so the "exactly 7 fields" assertion holds for
both seeded region pairs without touching the YAMLs.

### R2 — Use schema field names, not the names in BANKDEMO_INTEGRATION.md

`docs/BANKDEMO_INTEGRATION.md` lines 55–63 use aspirational paths
(`hlq.application`, `db2.subsystem`, `db2.collection`, `racf.user_default`,
`volser.primary`, `gating.override_required_role`) that don't match the
actual `RegionProfile` in `backend/app/models/region.py`. The schema is what
comes over the API and what tests assert against, so the schema wins.

`gating.override_required_role` is **out** of the substitution surface — it's
governance metadata, not text rewritten in JCL. `scheduler_queue` is **in**
because it's literally substitutable.

While Bob is in Plan mode, **also fix `docs/BANKDEMO_INTEGRATION.md`**
lines 55–63 to use the seven schema names from R1's table. This is a
docs-only edit, no behavior impact.

### R3 — Rounding bias has an explicit formula

The "biases up to avoid integer cliff" line in `docs/CONFIDENCE_SCORE.md` is
under-specified. The three worked examples (B: 60→62, C: 90→94, D: 100→100)
constrain it. The formula:

```python
def _apply_rounding_bias(raw: int, *, autofixes_remaining: int) -> int:
    """Bias scales with proximity-to-perfect.

    0 fixable findings remaining → +0 (raw is honest)
    1 fixable finding remaining  → +4 (signal "you're close")
    2+ fixable findings remaining → +2 (signal "fixable" without overselling)
    Cap at 100.
    """
    if raw >= 100:
        return 100
    bias = {0: 0, 1: 4}.get(autofixes_remaining, 2)
    return min(raw + bias, 100)
```

Verification against the three Worked Examples in `docs/CONFIDENCE_SCORE.md`:

- **B** (Maya first try): raw 60, two findings with `auto_fix` set
  (`backup_gap`, `copybook_drift`) → bias +2 → **62** ✓
- **C** (after backup fix): raw 90, one autofixable finding remaining
  (`copybook_drift`) → bias +4 → **94** ✓
- **D** (after both fixes): raw 100, zero autofixable remaining → bias 0 → **100** ✓

`autofixes_remaining` = `sum(1 for f in findings if f.auto_fix is not None)`.
The JJSCAN+ `RuleResult` schema already carries `auto_fix` (look at
`services/jjscan/framework.py`). When Bob lands `CopybookDriftRule.run`, the
rule emits its result with `auto_fix="update_syslib"`.

While Bob is in Plan mode, **also extend `docs/CONFIDENCE_SCORE.md`** with a
"Rounding bias" subsection that documents this formula verbatim. The doc
should mention the three worked examples as the contract test set.

Pin all three resolutions with tests:
- `tests/test_region_atlas.py::test_diff_int2_int3_uses_substitution_surface_only`
- `tests/test_region_atlas.py::test_diff_bnk_test_vsam_bnk_prod_seven_fields`
- `tests/test_score.py::test_rounding_bias_examples_b_c_d` (parametrize over
  the three worked examples)

---

## Read first (in this order)

1. `docs/PHASE_PLAN.md` §1.2 (Region Atlas), §1.3 (JJSCAN+ + Score), §1.4 (ABEND)
2. `docs/PERSONA_MAYA.md` Scene 1 + Scene 2 — these are the contracts the
   bodies must satisfy
3. `docs/CONFIDENCE_SCORE.md` — read the **Worked Examples A–D**. The 62 → 94
   → 100 ladder is what `compute()` must return for the seeded JCL
4. `docs/JJSCAN_PLUS_RULES.md` — full spec for the four rules; you're landing
   one and stubbing-with-empty-list the other three
5. `docs/REGION_PROFILE_SCHEMA.md` — fields the diff walks
6. `docs/BANKDEMO_INTEGRATION.md` — the seven int2/int3 (a.k.a.
   `bnk_test_vsam` / `bnk_prod`) fields that must surface in the diff
7. `docs/ABEND_PATTERN_LIBRARY.md` — confidence tiers + degraded path
8. `docs/AUDIT_LOG.md` — every state-changing endpoint must call
   `audit_writer.write_event` (lint rule enforces this in CI)
9. `docs/AGENTS.md` — hard rules; banned watsonx model list

Optional but useful:

- `backend/migrations/seed_demo.py` — see what's actually in the seeded
  Cloudant so the diff and score line up with reality
- `backend/tests/test_demo_smoke.py`, `backend/tests/test_abend_smoke.py` —
  the contracts you're flipping from xfail to green

---

## Mode plan

### Plan mode (~30 min)

Open Bob in Plan mode. Ask Bob to produce a file-by-file change list that
matches the scope below. Confirm:

- Every file in **Edit** is on the list and no others
- No file in **Do not touch** appears
- The proposed `compute()` formula matches `docs/CONFIDENCE_SCORE.md` Worked
  Examples A–D bytewise
- The proposed diff walker covers exactly the seven int2/int3 fields listed
  in `docs/BANKDEMO_INTEGRATION.md`

If Bob's plan deviates, push back before switching modes. A wrong plan in Code
mode burns coins fast.

### Code mode (~3 hours)

Switch to Code mode. Auto-approve writes only after the plan is locked.
If Bob proposes touching a file outside the Edit list, **stop and re-plan**.

### Plan-review export (~15 min)

After all tests are green, switch back to Plan mode for the audit-trail export
pass. Have Bob walk the diff, summarise the design choices, and produce the
session export to `bob_sessions/golden/<date>_scene_1_2_stubs/`. This export
is the judging artifact — make it real.

---

## Files to edit

### `backend/app/services/region_atlas.py`

Land both stubs. The functions are pure — no Cloudant access; the route
handlers fetch profiles and pass them in.

**`diff_regions(a, b) -> RegionDiffResponse`** — walk the
`SUBSTITUTION_SURFACE` constant (R1 above), emit a `DiffField` for every
path in the surface where the two profiles differ. `kind` ∈
{`value_change`, `added`, `removed`}. Dotted paths exactly as in
`SUBSTITUTION_SURFACE`. Order: stable (sort by path, or preserve the order
of `SUBSTITUTION_SURFACE` itself — pick one and lock it with a test).

For both seeded pairs (int2/int3, bnk_test_vsam/bnk_prod) all 7 surface paths
differ → diff returns 7 fields. Verified against current YAMLs in R1; no
seed fix needed.

P95 budget: well under 250 ms for two seeded profiles.

**`apply_substitutions(jcl_source, source, target) -> str`** — rewrite the
JCL along the same `SUBSTITUTION_SURFACE` paths. For each path where source
and target differ, find every literal occurrence of the source value in
`jcl_source` and replace with the target value. Substitution order matters
(longest source value first to avoid partial overlaps).

Preserve column-72 wrap and `*` continuation lines. Emit a structured trace
(list of `{path, before, after, line}`) — the Promote response surfaces it.

### `backend/app/services/score.py`

Land `compute(findings, context) -> (int, ScoreBreakdown)`.

Implement the formula from `docs/CONFIDENCE_SCORE.md`:

```
score = 100
      − Σ(severity_weight)
      − region_mismatch_count × 15
      − (30 if backup_gap else 0)
      − (5 × historical_abend_priors_30d)
      + (10 if spec_match else 0)
```

Then floor at 0, ceil at 100. Apply bonuses **after** penalties.

Apply the rounding bias from R3 above (`_apply_rounding_bias`). The bias is
the only non-trivial bit — implement it as the documented helper and cover
it with `tests/test_score.py::test_rounding_bias_examples_b_c_d` parametrized
over Worked Examples B/C/D from `docs/CONFIDENCE_SCORE.md`.

Region weight overrides: read `target_region.confidence_weight_overrides`
(that's the actual schema field — see `RegionProfile` in
`backend/app/models/region.py`) and override the defaults per-key. For
`bnk_prod` the YAML carries `critical: 50, high: 20, backup_gap: 60`. The
override is **absolute replacement**, not multiplicative — a `critical: 50`
override means a critical finding deducts 50, not 25 × 1.5.

### `backend/app/services/backup_generator.py`

Land `generate(request) -> BackupArtifact`.

Two methods:

- **VSAM** (e.g., `BNKACC.PATH3`) → `idcams_repro` template. Backup DSN:
  `<region_hlq>.BAK.<resource_short>.D<yyjjj>.T<hhmmss>` deterministic from
  request + a fixed UTC timestamp passed in (don't read `datetime.now` —
  tests need determinism; the call site can pass `now`).
- **DB2** protected table → `unload+image_copy` template (out of scope for
  Scene 1 since `BNKACC.PATH3` is VSAM, but please land both branches; the
  unload template is short). If the protected_resource isn't in the region's
  `protected_resources` list, raise `HeliosError(NOT_FOUND, ...)` — don't
  generate phantom backups.

JCL must be column-72 safe. Use real IDCAMS REPRO syntax (`INDATASET`,
`OUTDATASET`, `REPLACE`).

### `backend/app/services/jjscan/rules.py`

Land **`CopybookDriftRule.run`** (the Scene 1 finding). The other three rules
(`MissingProcMemberRule`, `ProcOverrideConflictRule`, `Db2PlanMismatchRule`)
**stay stubbed for this session**, but change them from
`raise NotImplementedError` to `return []` — empty findings list, so they
don't blow up the rule runner. Add a `# TODO(1.3 follow-up)` comment with the
JJSCAN spec section anchor.

`CopybookDriftRule.run`:

1. Parse all `COPY` statements in `ctx.jcl_source`.
2. For each copybook name, look up its current version in the source region's
   SYSLIB chain (`helios_jcl_artifacts` or whatever the seed loader populated
   — check `migrations/seed_corpus.py` or `seed_demo.py`).
3. Look up the version in the target region's SYSLIB chain.
4. Mismatch → emit a `RuleResult` with severity `MEDIUM`, the auto-fix
   `update_syslib`, and a non-empty `evidence` block.

The seeded data has `CBANKDAT.cpy` resolving to `v_VSAM` in `bnk_test_vsam`
and `v_SQL` in `bnk_pac` (and a similar drift for int2/int3). Verify the seed
matches; if not, fix the seed.

### `backend/app/services/abend_classifier.py`

Land `classify(input) -> AbendResponse`.

Pipeline:

1. Pattern match against the seeded `helios_abend_patterns` collection.
   Patterns key on regex over the dump. Return the highest-scoring match.
2. Confidence tiers per `docs/ABEND_PATTERN_LIBRARY.md`:
   - score ≥ 0.85 → `confirmed`
   - 0.6 ≤ score < 0.85 → `probable`
   - any extracted ABEND code with no library match → `unfamiliar`,
     `degraded=true`, `degraded_reason="no_pattern_match"`
   - nothing parseable → `unknown`
3. For `confirmed` / `probable`: ranked root causes (the pattern entry has
   them seeded), failing step (parse from JESYSMSG), source trace (line ref
   from the dump line), matching runbooks (Cloudant
   `helios_runbooks` filtered by `abend_code` + program).
4. `business_rule_explanation`: if watsonx is live, hit Granite Code with the
   prompt template at `services/granite_prompts.py`. If watsonx is in stub
   mode (no creds), set `business_rule_explanation=None` and
   `degraded_reason="watsonx_unavailable"` — don't fake it.

The Scene 2 fixture is `shared/sample-corpus/abend_examples/s0c7_custproc.txt`
(or `s0c7_bbank40p.txt` — check both, the seed uses one). It must classify
`S0C7`, `confirmed` tier, confidence ≥ 0.85.

### `backend/app/api/promote.py`

Remove the three `raise BobStubError` (lines 54, 67, 82). Wire the real
pipeline:

1. Load source + target region (`region_atlas.load_region`).
2. Run `region_atlas.diff_regions` for the response.
3. Run `region_atlas.apply_substitutions` to produce the rewritten JCL.
4. Run `JJSCAN+` rules over the rewritten JCL against the target region.
5. Run `score.compute` with the findings + region context.
6. If `auto_apply_fixes` includes `generate_paired_backup` and the score
   carries a backup_gap penalty: call `backup_generator.generate` for each
   protected resource the JCL touches.
7. **`audit_writer.write_event`** for the promote — required by lint
   (`tools/lint_audit_calls.py`). Subject `kind=jcl, name=<jcl_name>`, type
   `jcl_promote`, before/after the JCL source.
8. Return `audit_event_id`, `confidence_score`, `score_breakdown`, `findings`,
   `substitution_trace`, `generated_backup_jcl` (if any).

### `backend/app/api/jjscan.py`

Remove the `raise BobStubError` at line 199. Wire the real path through the
rule framework (it should already iterate `SEEDED_RULES`; the body just needs
the response shape filled in).

### `backend/migrations/seed_demo.py` / `backend/migrations/seed_corpus.py`

YAMLs already produce all 7 surface differences for both region pairs (see
R1's table). The only seed work is verifying — and possibly seeding —
`CBANKDAT.cpy` resolution into `helios_jcl_artifacts` so
`CopybookDriftRule.run` finds drift between source and target SYSLIB chains.
Check the seed loader; if the artifact rows aren't there for the int2/int3
pair, add them (the BankDemo pair already has them per the corpus loader).
Don't touch the region YAMLs.

### `docs/BANKDEMO_INTEGRATION.md` and `docs/CONFIDENCE_SCORE.md`

Two docs-only edits flagged in R2 and R3:

- `docs/BANKDEMO_INTEGRATION.md` lines 55–63: replace the seven aspirational
  paths with the seven canonical ones from R1's table.
- `docs/CONFIDENCE_SCORE.md`: add a "Rounding bias" subsection that
  documents R3's formula and pins it to the three Worked Examples.

---

## Files to NOT touch (hard)

- `frontend/**` — Sayan's territory; even passing through is a tripwire
- `bob_sessions/sayan/**` — Sayan's audit trail
- `test dataset/**` — read-only source corpus
- `.env`, `.env.example` — out of session scope
- `.bob/mcp.json` — config, not implementation
- `backend/app/services/audit_writer.py` — already real, do not "improve"
- `backend/app/services/cloudant.py` / `watsonx.py` — already real, including
  the banned-model guard. Do not add fallbacks that loosen it.

If Bob proposes editing any of the above, stop and re-plan.

---

## The contract — what "done" means

All of these go from xfail/red to green, with no new test failures:

```bash
make demo-smoke           # 8 steps, all green
make abend-smoke          # both seeded + degraded paths green
make verify-corpus        # corpus assertions still green
cd backend && pytest -q   # 149 tests stay green; xfails are removed where bodies landed
cd backend && ruff check . && ruff format --check .
cd backend && mypy app
python tools/lint_audit_calls.py    # promote endpoint passes
```

Specific endpoint shapes (these are what the production smoke script will hit):

- `GET /api/regions/int2/diff/int3` → 200, `data.fields` length **7**
- `POST /api/scan { jcl_name, region, target_region }` → 200, findings list
  contains `JJ-COPYBOOK-DRIFT-001` for the seeded JCL
- `POST /api/score { jcl_name, region: int3 }` → 200, `data.score == 62`
- `POST /api/promote { jcl, src, tgt, auto_apply_fixes: ["generate_paired_backup", "update_syslib"] }`
  → 200, `data.confidence_score == 100`, `data.audit_event_id` non-null
- `POST /api/abend { raw_text, context }` with seeded S0C7 → 200,
  `data.pattern_code == "S0C7"`, `data.tier == "confirmed"`,
  `data.confidence >= 0.85`
- `POST /api/abend` with novel pattern → 200, `data.degraded == true`,
  `data.tier == "unfamiliar"`

Remove the `@pytest.mark.xfail` markers in `test_demo_smoke.py` (lines 74,
84, 100, 111, 117) and `test_abend_smoke.py` (lines 25, 41) **only after the
corresponding endpoint actually returns the asserted shape**. Don't strip
markers as a "fix" without the body behind them.

---

## Hard constraints (non-negotiable)

These come from `CLAUDE.md` and `docs/AGENTS.md`. Bob enforces them in plan
mode; if Bob proposes a change that violates one, push back hard.

1. **No AI attribution anywhere.** No `Co-Authored-By: Bob/Claude/Granite` in
   commit messages. No "Generated with X" footers. No mention of Bob/Claude/
   Granite in code, comments, or docs (except in repo docs that already
   reference them — don't add new mentions).
2. **No banned watsonx models.** `llama-3-405b-instruct`,
   `mistral-medium-2505`, `mistral-small-3-1-24b-instruct-2503`. The runtime
   guard in `app/config.py:112` and `app/services/watsonx.py:64,142,193`
   stays intact. Don't loosen it.
3. **Audit writer is mandatory** for every state-changing endpoint. The lint
   rule (`tools/lint_audit_calls.py`) catches it in CI; don't disable.
4. **No `.env` edits, no secret values in any file.** Even in tests — use
   monkeypatched env vars or fixtures, never hardcoded keys.
5. **Type hints + ruff + mypy clean.** Backend code is type-checked.
6. **Conventional Commits** in human dev voice. Examples:
   - `feat(score): land confidence score formula with worked-example anchors`
   - `feat(jjscan): implement copybook drift rule`
   - `feat(region-atlas): structural diff + JCL substitution engine`
   - `feat(abend): pattern matcher + tiered confidence classifier`
   - `feat(promote): wire end-to-end pipeline through diff + score + backup`
7. **Determinism in tests.** No `datetime.now` inside services — pass `now`
   in. No random ordering — sort.

---

## Coin discipline

- Plan mode for the design walk. Don't act-mode through architectural
  decisions.
- One file at a time in Code mode. After each file, re-run that file's
  pytest module to confirm green. Cheaper than a "do everything then debug
  the mountain."
- If Bob hits a wall for 3+ minutes, stop and re-plan. The wall is usually a
  missing precondition (a seed that isn't loaded, an env var, a doc).
- Don't ask Bob to refactor anything that already works. The audit_writer,
  cloudant client, watsonx client, region IO functions, error handlers, JJSCAN
  framework, and route plumbing are all real today.

Rough budget: ~1 plan-mode session, ~5-7 act-mode invocations (one per file),
~1 plan-mode review. Should fit comfortably in the medium-coin envelope.

---

## When done

1. Show the diff to Golden.
2. `make demo-smoke && make abend-smoke && make verify-corpus` — all green.
3. Suggest commits as a sequence of conventional commits in human voice (see
   list above). Golden runs `git commit` himself.
4. Plan-mode review pass for the Bob session export to
   `bob_sessions/golden/<date>_scene_1_2_stubs/`. Make the export real — it's
   the judging audit trail. Do not inflate it.
5. Tell Golden: deploy is unblocked; resume the deployment-prep session.

---

## What's still owed after this session

For the audit_log of what's still on Bob's worklist:

- `MissingProcMemberRule`, `ProcOverrideConflictRule`, `Db2PlanMismatchRule`
  bodies (currently return `[]`)
- Promote auto-fix `update_syslib` actually rewriting the JCL (currently emits
  the trace but doesn't apply the fix)
- Runbook editor + creation flow (Phase 1.4 sub-task)
- Learning Loop dissent recompute (Phase 1.3 sub-task)

These are all next-session scope. The current session is the minimum that
unblocks deploy + makes both demo scenes work.
