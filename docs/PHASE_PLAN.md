# Phase Plan — How Helios Gets Built

The build is sequenced into six sub-phases under Phase 1 (the hackathon). Each has explicit exit criteria — a sub-phase isn't done until its criteria pass. **Do not start the next sub-phase before the current one passes.** Skipping forward is the most common way hackathon teams ship broken demos.

This is the operational counterpart to `docs/ROADMAP.md` (which describes Phase 1 / 2 / 3 / 4). Roadmap = strategy. Phase plan = execution.

---

## Why sequence at all

Two reasons.

1. **Hard dependencies.** `audit_writer` must exist before any state-changing endpoint, or every endpoint built first has to be retrofitted. Cloudant indexes must exist before queries can be tested. Region profiles must exist before Region Atlas can diff them.
2. **Demo confidence.** A demo that works end-to-end at 60% feature depth beats a demo that works at 90% depth on three pillars and crashes on the fourth. Sequencing keeps every pillar always-running.

The principle: **always have a working demo.** End of every sub-phase, you can rehearse.

## Total time budget

Hackathon timeline is 4 days. The plan fits in 3 days of build + 1 day of polish + rehearsal. Buffer is real — don't burn it.

| Sub-phase | Duration | Cumulative |
|---|---|---|
| 1.1 Foundations | 0.5 day | 0.5 |
| 1.2 Region Atlas | 0.75 day | 1.25 |
| 1.3 JJSCAN+ + Confidence Score | 0.75 day | 2.0 |
| 1.4 ABEND Archaeologist | 0.75 day | 2.75 |
| 1.5 Review Queue | 0.5 day | 3.25 |
| 1.6 Polish + rehearsals | 0.75 day | **4.0** |

Each "day" is ~10 working hours, both developers in parallel. Adjust if your team has different stamina.

---

## Phase 1.1 — Foundations (0.5 day)

The substrate everything else builds on. **No demo-visible features ship in this phase.** That's fine. Without these, nothing else works.

### Backend (Golden)

- [ ] Repo scaffold: `backend/{api,services,jobs,migrations,mcp,tests}/`
- [ ] `backend/main.py` FastAPI app skeleton with `/healthz` and `/readyz`
- [ ] Cloudant client wrapper: `backend/services/cloudant.py`
- [ ] Index migrations: `backend/migrations/cloudant_indexes.json` + `apply_indexes.py`
- [ ] **Audit writer**: `backend/services/audit_writer.py` with hash-chain + canonicalization
- [ ] Audit canonical test vectors: `backend/tests/audit_canonical_test_vectors.json`
- [ ] `helios-corpus` MCP server: `backend/mcp/corpus_server.py`
- [ ] `cloudant` MCP server: `backend/mcp/cloudant_server.py`
- [ ] `_seed.sh` for the MeridianBank corpus runs and verifies SHA-256

### Frontend (Sayan)

- [ ] Next.js 14 scaffold with App Router, static export configured
- [ ] Tailwind config + design tokens (color, spacing, typography)
- [ ] Auth bootstrap: `/login` page that hits `POST /auth/login`, stores JWT
- [ ] Layout shell: top nav, sidebar with feature tabs (Atlas / Studio / ABEND / Audit / Review)
- [ ] WebSocket hook scaffold: `frontend/lib/useReviewQueue.ts` (subscriber only, no UI yet)
- [ ] Empty state for every tab — "no data yet" placeholder copy

### Exit criteria

- `curl localhost:8080/healthz` returns ok
- `curl localhost:8080/readyz` returns ok with both Cloudant + watsonx reachable
- `make demo-smoke` passes through step 3 (login as Maya)
- Bob IDE shows green dots for `helios-corpus` and `cloudant` custom MCP servers
- Frontend renders the empty layout shell at `localhost:3000`
- Audit writer test vectors all pass

If any criterion fails, **fix it before starting 1.2**. Foundations debt compounds.

---

## Phase 1.2 — Region Atlas (0.75 day)

The first demo-visible pillar. Targets the "tribal knowledge in three Confluence pages" pain.

### Backend (Golden)

- [ ] Region profile schema validator: `backend/services/region_schema.py`
- [ ] Seed data loader for 7 regions: `backend/migrations/seed_regions.py`
- [ ] `GET /api/regions` and `GET /api/regions/{name}` endpoints
- [ ] `GET /api/regions/{a}/diff/{b}` — the diff engine, returns field-by-field changes
- [ ] `POST /api/regions/{name}` — create/update with audit event
- [ ] `POST /api/regions/{name}/forks/{job_name}` — job-specific override layer
- [ ] Substitution engine: `backend/services/region_atlas.py::apply_substitutions(jcl, source_region, target_region)`

### Frontend (Sayan)

- [ ] Atlas tab: list of 7 regions as cards
- [ ] Region detail view: full profile in collapsible YAML-like layout
- [ ] **Diff view:** side-by-side using Monaco diff editor, hover-reasons, color-coded changes
- [ ] Promote wizard skeleton: source region picker, target region picker, "Run Promote" button (not wired yet)

### Exit criteria

- Diff between `int2` and `int3` shows exactly 7 highlighted fields per `docs/PERSONA_MAYA.md` Scene 1
- Demo flow: open Atlas → click `int2` → click "Diff with int3" → diff renders in <250ms (P95 budget per `docs/TESTING.md` §5)
- Audit log has events for the 7 region creations from seed
- Promote wizard renders but doesn't yet call the backend (`POST /api/promote` doesn't exist yet)

---

## Phase 1.3 — JJSCAN+ + Confidence Score (0.75 day)

The two pillars that work together. Score is a wrapper over JJSCAN+ findings + region mismatch + backup gap + historical ABEND priors.

### Backend (Golden)

- [ ] `backend/services/jjscan/` rule framework: `Rule` base class, `RuleResult` schema
- [ ] **Four rules implemented with golden tests:**
  - `JJ-COPYBOOK-DRIFT-001`
  - `JJ-MISSING-PROC-MEMBER-001`
  - `JJ-PROC-OVERRIDE-CONFLICT-001`
  - `JJ-DB2-PLAN-MISMATCH-001`
- [ ] `POST /api/scan` endpoint (source-string and named-JCL forms)
- [ ] `POST /api/scan/findings/{id}/decide` (accept/dismiss with reason tags)
- [ ] `POST /api/scan/findings/{id}/auto-fix`
- [ ] Confidence Score engine: `backend/services/score.py::compute(findings, context)`
- [ ] `POST /api/score` endpoint for ad-hoc scoring
- [ ] `POST /api/promote` endpoint (the hero endpoint per `docs/API.md` §5)
- [ ] Backup generator: `backend/services/backup_generator.py` (UNLOAD + IMAGE COPY for protected DB2; IDCAMS REPRO for VSAM)
- [ ] Learning Loop dissent query: `GET /api/learning/dissent`

### Frontend (Sayan)

- [ ] Studio tab: JCL list, JCL viewer (Monaco read-only)
- [ ] Promote button on JCL viewer — wires up the wizard from 1.2
- [ ] **Confidence Score gauge** (Recharts radial), 62/RED → 94 → 100/GREEN transitions
- [ ] Score breakdown panel — every component visible per `docs/CONFIDENCE_SCORE.md`
- [ ] Findings list with severity badges
- [ ] **Dissent banner** on each finding ("Your shop dismissed this 7 of 9 times…") per `docs/LEARNING_LOOP.md`
- [ ] Auto-fix buttons for each finding with available auto-fix
- [ ] Reason tag picker for accept/dismiss

### Exit criteria

- Promoting `CUST_DELETE_INACTIVE.JCL` int2 → int3 with no auto-fixes returns score = 62 (asserted in smoke test)
- Applying both auto-fixes returns score = 100
- Dissent banner appears on the seeded copybook drift finding showing 7/9
- The `make demo-smoke` 8-step round-trip from `docs/TESTING.md` §2 passes end-to-end

This is the demo's centerpiece. Rehearse Scene 1 (Maya's promote) at the end of this phase even though the Review Queue doesn't exist yet — you can fake the Anil approval with a console click.

---

## Phase 1.4 — ABEND Archaeologist (0.75 day)

The third pillar. Targets the "grep on 12,000-line SYSLOGs" pain.

### Backend (Golden)

- [ ] ABEND family taxonomy: `backend/services/abend_families.py`
- [ ] ABEND classifier with confidence tiers (confirmed/probable/unfamiliar/unknown) per the new `ABEND_PATTERN_LIBRARY.md` § Unknown ABEND handling
- [ ] Pattern library — ~15 seeded patterns: `backend/services/abend_patterns/*.py`
- [ ] Pre-seeded entries in `helios_abend_patterns` collection from `_seed.sh`
- [ ] `POST /api/abend` endpoint with degradation logic (`degraded`, `degraded_reason` fields)
- [ ] `POST /api/abend/{event_id}/resolve` writes learning event
- [ ] Granite Code prompt template for paragraph summarization: `backend/services/granite_prompts.py`
- [ ] `watsonx` MCP server: `backend/mcp/watsonx_server.py`
- [ ] Runbook generator + lookup: `GET /api/runbooks?abend_code=X&program=Y`
- [ ] `POST /api/abend/{event_id}/resolve` → optionally creates a new runbook entry

### Frontend (Sayan)

- [ ] ABEND tab with three-pane layout (SYSLOG paste / source view / analysis)
- [ ] SYSLOG paste box with parser feedback (highlights what was extracted)
- [ ] Source view (Monaco read-only) jumps to the failing line, highlights paragraph + field
- [ ] Analysis pane: identified ABEND, confidence, ranked root causes, matching runbooks
- [ ] **Unfamiliar-tier banner** per the new `ABEND_PATTERN_LIBRARY.md` section — "hasn't seen this pattern before" CTA
- [ ] One-click "Apply quarantine SQL" button (gated by `confirmed` tier)
- [ ] Runbook viewer

### Exit criteria

- `make abend-smoke` passes (S0C7 in CUSTPROC → all assertions green per `docs/TESTING.md` §3)
- `make abend-smoke-degraded` passes (unfamiliar tier extraction works without priors)
- Scene 2 from `docs/PERSONA_MAYA.md` rehearses cleanly in <1 minute
- Granite Code summary returns within P95 budget (3 s) per `docs/TESTING.md` §5

---

## Phase 1.5 — Review Queue (0.5 day)

The two-developer real-time feature. Ties everything together.

### Backend (Golden)

- [ ] Cloudant `_changes` listener: `backend/services/audit_listener.py`
- [ ] WebSocket endpoint: `backend/api/ws_queue.py` with per-user RBAC filter
- [ ] Heartbeat (ping/pong every 25 s)
- [ ] `GET /api/queue` and `GET /api/queue/since?seq=X` (polling fallback)
- [ ] `POST /api/queue/{event_id}/approve` / `reject` (initiator-can't-self-review enforcement)
- [ ] Auto-approve policy engine reading `config/review_queue_defaults.yaml`

### Frontend (Sayan)

- [ ] Review tab with badge showing pending count
- [ ] Per-event card with score, top reasons, auto-fixes summary, View Diff / Approve / Reject buttons
- [ ] **Mobile-responsive layout** for the queue (this is the split-screen demo moment)
- [ ] Reconnect-with-backoff logic in `useReviewQueue` hook
- [ ] Polling fallback when WebSocket unreachable
- [ ] Toast notifications for both initiator (approval received) and reviewer (new pending)

### Exit criteria

- The split-screen demo: laptop signed in as Maya, second device signed in as Anil. Maya clicks Promote → toast on Anil's device within 800 ms (per `docs/REVIEW_QUEUE.md`)
- Anil approves → toast on Maya's tab within 800 ms
- Audit log shows the request and the approval as separate events
- Killing the WebSocket process mid-flow → frontend falls back to polling, demo continues with 3 s lag (per `docs/TESTING.md` §4 S3)

---

## Phase 1.6 — Polish + rehearsals (0.75 day)

No new features. Everything is about confidence on demo day.

### Both developers

- [ ] Run `make demo-smoke` and `make abend-smoke` — both green
- [ ] Run resilience scenarios S1-S6 from `docs/TESTING.md` §4 — all green
- [ ] Capture hero shots per `docs/HERO_SHOTS.md` — pixel-exact
- [ ] Record demo dry-run as MP4, watch back, identify lag/awkward moments
- [ ] Rehearse Scene 1 + Scene 2 + audit query trick (`docs/TESTING.md` §6) at least 3 times
- [ ] Final `make benchmark` run — numbers committed to `bench/results/`
- [ ] Print and tape the pre-demo checklist (`docs/TESTING.md` §7) next to the demo laptop
- [ ] Both Bob session histories exported to `bob_sessions/` (judging deliverable)

### Exit criteria

- All `make` targets pass
- Demo runs in <90 seconds, both scenes
- Two devs can swap demo-driver mid-rehearsal without confusion
- Performance budgets in `docs/TESTING.md` §5 all met
- README has the hero GIF + the 4 metrics from `docs/CORPUS.md` Ground-truth metrics
- DOCS_INDEX is current — every doc cross-referenced exists

If any of these is no, **stop and fix that one** before the submission deadline.

---

## Hard dependencies — explicit

Some things must exist before others. Violate at peril.

| Must exist | Before |
|---|---|
| `audit_writer.py` + Cloudant indexes | Any state-changing endpoint |
| Region profiles seeded | Region Atlas diff |
| JJSCAN+ rule framework | Confidence Score (it consumes findings) |
| Confidence Score engine | `POST /api/promote` (it returns the score) |
| ABEND pattern library + classifier | `POST /api/abend` |
| WebSocket endpoint + audit listener | Review Queue UI (UI can use polling fallback temporarily) |
| `frontend/lib/api.ts` typed against `docs/API.md` | Any frontend feature that calls the backend |

The lint rule `tools/lint_audit_calls.py` enforces #1 in CI; the others are human discipline.

## Branching model during the build

Per sub-phase, both devs work on parallel feature branches that share the sub-phase prefix:

```
feat/1.1-audit-writer        (Golden)
feat/1.1-frontend-shell      (Sayan)
feat/1.2-region-diff         (Golden)
feat/1.2-atlas-tab           (Sayan)
…
```

PRs merge into `main` as each sub-component lands. The exit criteria of a sub-phase = "all PRs for that sub-phase merged + smoke tests green."

## What this plan is NOT

- Not the strategy — that's `docs/ROADMAP.md`
- Not the daily flow — that's `docs/WORKFLOW.md`
- Not the test regime — that's `docs/TESTING.md`
- Not the demo script — that's `docs/DEMO_SCRIPT.md`

## One sentence

> Six sub-phases, each with a working demo at the end, foundations before features, audit_writer before anything that touches state, Confidence Score before Promote, Review Queue last because it ties everything together. Polish is a phase, not a leftover.
