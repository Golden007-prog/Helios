# Risk Register

Every risk that could sink the submission, with mitigation and owner. Reviewed at start of every working day.

---

## Risk severity scale

- **Critical** — submission fails or demo collapses if it materializes
- **High** — significant scope cut required
- **Medium** — recoverable with effort
- **Low** — annoying but not project-threatening

---

## Active risks

### R-01 — Bobcoin exhaustion before demo

- **Severity:** Critical
- **Owner:** both
- **Probability:** Medium
- **Trigger:** Either team member's Bobcoin balance drops below 5 with > 8 hours of work remaining.
- **Mitigation:**
  - [`docs/BOBCOIN_BUDGET.md`](BOBCOIN_BUDGET.md) defines per-task allocation; track in `bob_sessions/<owner>/COIN_LOG.md`
  - Default to Plan mode; switch to Code only after plan is good (5x cheaper)
  - Disable unused MCP servers in Bob settings
  - Golden has Claude Code as silent fallback; Sayan pairs from Golden's machine if Sayan exhausts first
- **Detection:** Daily check at session start. If running ahead of budget, escalate immediately.

### R-02 — IBM hackathon account suspended

- **Severity:** Critical
- **Owner:** both
- **Probability:** Low
- **Trigger:** Account flagged for using a banned watsonx model (`llama-3-405b-instruct`, `mistral-medium-2505`, `mistral-small-3-1-24b-instruct-2503`), or for committing IBM Cloud secrets to a public repo (GitHub secret scanning will report).
- **Mitigation:**
  - Hard-coded model allow-list in `backend/services/llm/models.py` — banned models can't be selected
  - Pre-commit hook scans for `IBM_CLOUD_API_KEY=`, `WATSONX_API_KEY=`, `ghp_` prefixes
  - `.gitignore` includes `.env*`, all PAT files, all credential JSON files
  - Read [`SECURITY.md`](SECURITY.md) before any session; if you commit a secret, rotate it within 5 minutes
- **Recovery:** None practical. Prevention is the only path.

### R-03 — IBM Cloud credit exhaustion

- **Severity:** High
- **Owner:** Golden
- **Probability:** Low (we have $80, projected spend ~$15)
- **Trigger:** watsonx.ai inference burning more than projected; Code Engine scaling to multiple instances.
- **Mitigation:**
  - Cache watsonx responses in Cloudant by `(prompt_hash, model)` for 24h
  - Limit Code Engine `max_scale` to 2 instances during dev, 5 during demo
  - Daily check: IBM Cloud → Billing → Usage. Alert at 50% of $80.
- **Recovery:** Disable watsonx-backed features (JJSCAN+ explanations, ABEND business explanation). Demo from cached responses.

### R-04 — No real LPAR / mainframe access

- **Severity:** High (already accepted)
- **Owner:** both
- **Probability:** 100% (we don't have one)
- **Mitigation:**
  - Build the **MeridianBank synthetic shop** in `shared/sample-corpus/`: 5 COBOL programs, 3 copybooks, 6 region profiles, 2 DB2 tables, 10 seeded ABEND incidents
  - Source: GnuCOBOL test suite + opensourcecobol/Bankdemo + NIST COBOL85, rebadged as MeridianBank
  - JCL parsed statically — never executed
  - SMF-shaped synthetic events for any anomaly demos
  - Pitch the corpus quality intentionally — judges who know mainframes will recognize Bankdemo as a respectable foundation
- **Implication:** Helios is positioned as a **control plane**, not an execution engine. We never claim to submit to JES.

### R-05 — Demo failure on judging day

- **Severity:** Critical
- **Owner:** Sayan (presenting), Golden (backup)
- **Probability:** Medium
- **Triggers:**
  - Code Engine cold start makes backend unresponsive for 30+ seconds
  - watsonx.ai latency spike > 10 seconds
  - GitHub Pages deploy stale or 404
  - WiFi flaky in the demo room
  - Live ABEND demo doesn't match the pre-loaded sample
- **Mitigation:**
  - **Pre-recorded 90-second demo video as fallback** — record by morning of judging day
  - Pre-warm Code Engine 30 minutes before demo (curl `/healthz` every 5 minutes)
  - Cache all demo-flow watsonx responses in Cloudant; serve from cache if API > 3 sec
  - Local `npm run dev` ready as backup if GitHub Pages stale
  - Mobile hotspot pre-paired and tested; both presenters on same network
  - Pre-loaded "demo dump" in ABEND Archaeologist with known-good detection result
- **Recovery:** Switch to backup video. Narrate over it. Most judges will not notice.

### R-06 — Merge hell from parallel work

- **Severity:** Medium
- **Owner:** both
- **Probability:** Medium
- **Trigger:** Two PRs touch the same file in `shared/` or `docs/`.
- **Mitigation:**
  - Hard ownership rules in [`TEAM_WORKSPACE.md`](TEAM_WORKSPACE.md): never edit other person's top-level dir without coordination
  - Daily sync ritual at session start: `git log --since="12 hours ago" --author=<other>` + 60-sec voice call
  - Branch names include owner: `feat/<owner>/<task>` — visible at a glance
  - PRs reviewed within 30 minutes; long-lived branches forbidden (4-hour lifetime cap)
- **Recovery:** PR opened later resolves the conflict; pair on the merge if non-trivial.

### R-07 — Bob session reports not exported / incomplete

- **Severity:** Critical (judging deliverable)
- **Owner:** each owns their own
- **Probability:** High if not disciplined
- **Trigger:** End-of-session ritual skipped; reports left as drafts or unexported.
- **Mitigation:**
  - 15-minute end-of-session timer (see [`WORKFLOW.md`](WORKFLOW.md))
  - PR template requires confirming session report committed for that task
  - Daily sync checks: "Have you exported reports for today's tasks?"
- **Recovery:** Limited. Bob does retain task history — re-export on the morning of judging if needed, but exports lose fidelity if the chat was condensed.

### R-08 — watsonx.ai banned model accidentally invoked

- **Severity:** Critical
- **Owner:** Golden
- **Probability:** Low
- **Mitigation:**
  - Hard allow-list: `backend/services/llm/models.py` exposes only `granite-code-8b`, `granite-3-8b-instruct`
  - All inference calls go through this module; no direct `httpx` calls to watsonx in feature code
  - Code review checklist item: "Does this PR add or change inference call sites?"
- **Recovery:** Immediately remove the call, investigate any IBM warning email, document in this register.

### R-09 — Cloudant Lite tier rate limit hit

- **Severity:** Medium
- **Owner:** Golden
- **Probability:** Medium during demo (multiple judges loading at once)
- **Trigger:** > 20 reads/sec sustained.
- **Mitigation:**
  - Read-through cache in FastAPI for region profiles + audit log queries (TTL 60s for regions, 5s for audit)
  - Demo flow queries pre-warmed in cache before judging
  - WebSocket Review Queue updates push from server, not polled
- **Recovery:** Demo from local fixtures if Cloudant unresponsive (worst case).

### R-10 — GitHub Actions deploy fails

- **Severity:** Medium
- **Owner:** Golden (backend deploy), Sayan (frontend deploy)
- **Probability:** Low
- **Trigger:** Workflow timeout, secret missing, build error.
- **Mitigation:**
  - Both deploy workflows tested end-to-end in Phase 1
  - Status badge on README — `main` branch deploy state visible
  - Each PR tested via `act` locally before merge if it touches workflow files
- **Recovery:** Manual deploy from local machine using `ibmcloud ce app update` (backend) or `gh-pages` npm script (frontend).

### R-11 — Demo corpus too small / unconvincing

- **Severity:** High
- **Owner:** Sayan + Golden (both seed)
- **Probability:** Medium
- **Trigger:** Judges press for "show me a different program" and we have only one demo path.
- **Mitigation:**
  - Seed at least 5 distinct COBOL programs in MeridianBank
  - Seed at least 3 different ABEND scenarios beyond the demo one
  - Pre-stage 2 "alternate runs" of the Maya scenario with different region pairs (int1→int2, dev3→int1) so judges can ask for variety
- **Recovery:** Acknowledge limitation, pivot to roadmap discussion ("the architecture supports any region map; we seeded MeridianBank for the demo").

### R-12 — Time underestimated

- **Severity:** High
- **Owner:** both
- **Probability:** Always
- **Trigger:** Phase 3 (the depth features) takes 2x longer than planned.
- **Mitigation:**
  - Phase plan in [`PHASE_PLAN.md`](PHASE_PLAN.md) commits to **shipping 4 detection rules in JJSCAN+, not 9**
  - ABEND Archaeologist ships with **15 pre-seeded patterns**, not unbounded
  - Confidence Score formula is a **fixed default**, not a UI-tunable one (config file only)
  - "Done is better than perfect" — Phase 5 polish is timeboxed at 4 hours
- **Recovery:** Cut features in this order: voice demo (STT/TTS), Confidence Score per-region overrides, JJSCAN+ rules 5–9, audit CSV export, learning loop visibility in UI.

### R-13 — Reviewer offline at critical moment

- **Severity:** Low
- **Owner:** both
- **Probability:** High (small team, different time zones possible)
- **Mitigation:**
  - `gh pr merge --auto --squash` on every PR — merges when CI passes
  - CI gates: ruff + pytest + frontend build + lint
  - Trust the CI; manual review can happen post-merge for non-critical changes
- **Recovery:** None needed; auto-merge handles it.

### R-14 — Granite Code 8B output quality on COBOL is weaker than expected

- **Severity:** High
- **Owner:** Golden
- **Probability:** Low (Granite is genuinely strong on COBOL)
- **Trigger:** ABEND business explanations or copybook drift explanations are vague or wrong.
- **Mitigation:**
  - Heavy prompt engineering in `shared/prompts/` — temperature 0.2, system prompts laden with COBOL-specific context
  - Fall back to `granite-3-8b-instruct` with COBOL excerpts as user-provided context if Granite Code is weak on a specific task
  - Pre-validate every demo response in advance and cache the good ones
- **Recovery:** Demo runs from cache, not live inference.

---

## Closed risks (informational)

### R-00 — Should we attempt to fake a real LPAR connection?

- **Decision:** No. Time sink, judges can detect, and damages the credibility of the genuine work. Move scope to a high-quality synthetic corpus instead. (Decided week 1.)

---

## Risk review cadence

- **Daily:** session start. 60 seconds. New risks added, status checked.
- **Pre-demo (4 hours before):** full register walkthrough. Pre-recorded video confirmed. Backups in place.
