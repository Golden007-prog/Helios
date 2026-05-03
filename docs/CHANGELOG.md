# Changelog

All notable changes to Helios. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

---

## [v1.0-hackathon] — IBM Bob Dev Day Hackathon submission

### Added — Phase 1 (foundation)
- Repo scaffolding: monorepo layout with `frontend/`, `backend/`, `mcp-servers/`, `shared/`, `docs/`, `bob_sessions/`
- `.bob/mcp.json` with off-the-shelf MCP servers (github, filesystem, memory, fetch) enabled and four custom Helios MCP servers wired but disabled
- `AGENTS.md` for Bob IDE shared context
- Local `CLAUDE.md` template for Golden's silent Claude Code partner (gitignored)
- `.gitignore` covering secrets, `.claude/`, build artefacts
- `.env.example` with all environment variable placeholders
- FastAPI backend skeleton with `/healthz`, `/version`, structured logging
- Next.js 14 frontend skeleton with Tailwind, shadcn/ui, four-tab layout
- GitHub Actions test workflow on every PR
- GitHub Actions deploy workflows for backend (Code Engine) and frontend (GitHub Pages)
- Cloudant connection helper, database initialization scripts
- Region profile JSON Schema validation

### Added — Phase 2 (Region Atlas + custom MCP servers)
- Region profile YAML schema with seven default MeridianBank regions seeded
- Region CRUD API (`GET/PUT /regions/{name}`, `POST /regions/{a}/diff/{b}`)
- Promote-job logic with parameter substitution and reasoning
- Pre-flight backup generator: DB2 `UNLOAD + IMAGE COPY` and VSAM `IDCAMS REPRO`
- Custom MCP server: `cloudant` (CRUD against Helios Cloudant collections)
- Custom MCP server: `watsonx` (Granite Code 8B inference)
- Custom MCP server: `helios-corpus` (MeridianBank synthetic shop access)
- Custom MCP server: `ibm-cloud` (deploys + service management)
- Studio UI: region picker, region YAML editor (Monaco two-pane)
- Studio UI: **Region Atlas diff view** (hero shot 1) — side-by-side YAML diff with hover-over reasoning

### Added — Phase 3 (JJSCAN+ + ABEND Archaeologist + Confidence Score)
- JCL parser (~400 lines, hand-written in `backend/parsers/jcl.py`)
- COBOL parser glue via ProLeap (subprocess)
- Dependency resolver across SYSLIB concatenation order
- JJSCAN+ rules (Phase 1):
  - `copybook_drift` (high)
  - `missing_proc_member` (critical)
  - `proc_override_conflict` (high)
  - `db2_plan_mismatch` (critical)
- ABEND Archaeologist pattern matcher with regex + token-similarity scoring
- 15 pre-seeded ABEND patterns covering COBOL, JCL, DB2 failures
- COBOL traceback engine (MOVE chain walker)
- Granite Code prompts for business-rule explanation
- Runbook synthesizer
- Confidence Score calculator with default weights and per-region overrides
- Studio UI: JJSCAN+ panel with findings list and severity badges
- Studio UI: React Flow dependency graph with click-to-expand
- Archaeology UI: **ABEND three-pane view** (hero shot 3) — dump → trace → business explanation
- Archaeology UI: runbook draft view with "save to library" button
- **Confidence Score gauge** (hero shot 2) — D3 SVG arc with traffic-light coloring and animation
- Top-3-reasons display with "fix" buttons; "Override score" modal with reason input

### Added — Phase 4 (audit + review + deploy)
- Audit log query API with filtering
- Audit log viewer with CSV export
- Review Queue WebSocket hub (subscribed to Cloudant change feed)
- Real-time toast notifications for promotions awaiting review
- Code Engine production deploy with secrets configured
- GitHub Pages production deploy
- End-to-end smoke tests against deployed backend

### Added — Phase 5 (polish + measurement)
- Loading states with shimmer placeholders
- Micro-interactions (button hover, score pulse, toast slide-in)
- Empty states for every panel
- Final dark-mode contrast pass
- Demo screen layout optimization
- 90-second backup demo video
- Quantified before/after measurements in README:
  - JCL promotion: 47 min → 6 min
  - ABEND root cause: 4.3 hr → 4 min
  - First-prod-run ABEND rate: 18% → 0%
- All Bob session reports exported to `bob_sessions/golden/` and `bob_sessions/sayan/`
- Bobcoin spend logs finalized

### Documentation
- `README.md` — main project entry with problem, solution, tech stack, doc index
- `docs/PROBLEM_STATEMENT.md` — the mainframe modernization pain we attack
- `docs/ARCHITECTURE.md` — System Architecture Diagram + sequence diagram + deployment topology
- `docs/SPECS.md` — feature-by-feature specification
- `docs/CONFIDENCE_SCORE.md` — formula, weights, override mechanism
- `docs/REGION_PROFILE_SCHEMA.md` — YAML schema field reference
- `docs/JJSCAN_PLUS_RULES.md` — full rule library with Phase 1 demo + Phase 2 roadmap
- `docs/ABEND_PATTERN_LIBRARY.md` — 15 seeded patterns with matching algorithm
- `docs/MCP_SETUP.md` — Bob IDE + Claude Code MCP configuration
- `docs/WORKFLOW.md` — daily dev flow, Git, Bob session export
- `docs/TEAM_WORKSPACE.md` — two-developer parallel work, ownership boundaries
- `docs/BOBCOIN_BUDGET.md` — 40 coins per person allocation and tracking
- `docs/DEMO_SCRIPT.md` — Maya scenario, scene by scene, hero shots
- `docs/JUDGING_ALIGNMENT.md` — rubric mapping
- `docs/QA_PREP.md` — top 10 anticipated judge questions
- `docs/RISK_REGISTER.md` — known risks with mitigations
- `docs/SECURITY.md` — secrets, audit, incident response
- `docs/TOOLS_AND_SERVICES.md` — every tool, library, free tier
- `docs/PHASE_PLAN.md` — five-phase build sequence with time budgets
- `docs/DEPLOYMENT.md` — GitHub Actions workflows
- `bob_sessions/README.md` — session export instructions
- `CONTRIBUTING.md` — branch rules and PR template
- `docs/templates/CLAUDE.md.template` — Claude Code silent-partner rules
- `docs/templates/PR_TEMPLATE.md` — PR description template

### Decisions documented
- Chose **3 deep features** (Region Atlas, JJSCAN+, ABEND Archaeologist) over 13 shallow ones
- Chose **Confidence Score** as the single number tying all features together
- Chose **MeridianBank synthetic corpus** over attempting to fake real LPAR access
- Chose **Bob IDE as the visible AI partner** for judging; Claude Code stays silent (Golden only)
- Chose **Granite Code 8B** over larger models (cost, latency, hackathon banned-list compliance)
- Chose **Cloudant Lite** over a SQL database (JSON-native, change feed for Review Queue)
- Chose **GitHub Pages + Code Engine** over a single monolithic deploy (free, faster CI, decouples failure modes)

### Out of scope (intentionally deferred to v2)
- Real LPAR connection (FTP/SFTP, JES submission, SMF event ingestion)
- CICS / IMS resource management (schema is forward-compatible)
- COBOL → Java translation (complementary to Watson Code Assistant for Z, not competitive)
- RBAC / SSO inside Helios (every authenticated user has full access in demo)
- ML-learned Confidence Score weights (keep formula static for hackathon predictability)
- JJSCAN+ rules 5–9 (documented as roadmap)
- Voice demo (STT/TTS) — bonus, cut for time
- Notion/Confluence runbook export — Cloudant + markdown view in Helios UI is enough

---

## How to read this changelog

Each entry maps roughly to a phase in [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md). The "Decisions documented" section captures the rationale behind major scope choices — useful for judges asking *"why did you do it this way?"* and for any future maintainer.

The "Out of scope" section is intentional. Honesty about what we didn't build is more credible than pretending we shipped enterprise SSO in a weekend.

---

## Future versions

### [v1.1] — first post-hackathon release (planned)
- LPAR agent for SMF / SYSLOG ingestion
- JJSCAN+ rules 5–9 (GDG version misalignment, restart-step incompatibility, dead branch, circular includes, missing SYSLIB member)
- Per-team Confidence Score profiles
- RBAC v1 (RACF group passthrough)

### [v1.2] — production hardening
- SSO via SAML/OIDC
- Audit log tamper-evidence (hash chain)
- Multi-tenant deployment model
- Score trend analytics

### [v2.0] — closed-loop platform
- Two-way LPAR sync (read events + write JCL)
- Live Confidence Score updates as upstream conditions change
- Predictive ABEND warnings before submission
- Auto-generated test cases from spec files
