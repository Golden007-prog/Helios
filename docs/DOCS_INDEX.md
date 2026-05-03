# Documentation Index

The full map of every document in this repo. Use this when you need to know if something has already been written, before reaching for Bob to write it again.

Last updated: hackathon kickoff. If you add a doc, add it here.

---

## By role: where to start

**If you're Golden (backend, MCP, infra)** read in this order:
1. [`KICKOFF_CHECKLIST.md`](docs/KICKOFF_CHECKLIST.md)
2. [`AGENTS.md`](AGENTS.md)
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
4. [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md)
5. [`docs/SPECS.md`](docs/SPECS.md)
6. [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md)
7. [`docs/templates/CLAUDE.md.template`](docs/templates/CLAUDE.md.template)

**If you're Sayan (frontend, demo polish)** read in this order:
1. [`KICKOFF_CHECKLIST.md`](docs/KICKOFF_CHECKLIST.md)
2. [`AGENTS.md`](AGENTS.md)
3. [`docs/PERSONA_MAYA.md`](docs/PERSONA_MAYA.md)
4. [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)
5. [`docs/HERO_SHOTS.md`](docs/HERO_SHOTS.md)
6. [`docs/SPECS.md`](docs/SPECS.md)
7. [`docs/BOBCOIN_BUDGET.md`](docs/BOBCOIN_BUDGET.md)

**If you're a judge or visitor** read in this order:
1. [`README.md`](README.md)
2. [`docs/PROBLEM_STATEMENT.md`](docs/PROBLEM_STATEMENT.md)
3. [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
5. [`docs/JUDGING_ALIGNMENT.md`](docs/JUDGING_ALIGNMENT.md)

---

## By category

### Top-level repo files

| File | Purpose |
|---|---|
| [`README.md`](README.md) | Pitch, demo link, stack overview, repo layout, team |
| [`AGENTS.md`](AGENTS.md) | Project context Bob IDE reads on every task |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Branch model, commits, PR rules, review checklist |
| [`CHANGELOG.md`](CHANGELOG.md) | Phase-by-phase history of what shipped when |
| [`LICENSE`](LICENSE) | Apache 2.0 (full text) |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Contributor Covenant 2.1 community standards |
| [`SUPPORT.md`](SUPPORT.md) | Where and how to ask for help |
| [`.gitignore`](.gitignore) | Secrets, `.claude/`, `CLAUDE.md`, build artefacts |
| [`.env.example`](.env.example) | Template for required environment variables |
| [`.bob/mcp.json`](.bob/mcp.json) | Shared, project-level MCP server config |

### Strategy and judging

| File | What it answers |
|---|---|
| [`docs/PROBLEM_STATEMENT.md`](docs/PROBLEM_STATEMENT.md) | Why mainframe modernization sucks today; the three pains we attack |
| [`docs/PERSONA_MAYA.md`](docs/PERSONA_MAYA.md) | The user we're building for, scene by scene |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | The 90-second demo flow, with timing and speaking roles |
| [`docs/HERO_SHOTS.md`](docs/HERO_SHOTS.md) | Pixel-level specs for the three demo-day visual centerpieces |
| [`docs/JUDGING_ALIGNMENT.md`](docs/JUDGING_ALIGNMENT.md) | How every feature maps to the 5+5+5+5 = 20 rubric |
| [`docs/QA_PREP.md`](docs/QA_PREP.md) | Top 10 anticipated judge questions with prepped answers |

### Architecture and specs

| File | What it answers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System Architecture Diagram, sequence flows, deployment topology |
| [`docs/SPECS.md`](docs/SPECS.md) | Feature-by-feature specification (the four pillars) |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Cloudant collections, document shapes, indexes |
| [`docs/REGION_PROFILE_SCHEMA.md`](docs/REGION_PROFILE_SCHEMA.md) | Full YAML schema for region profiles with validation rules |
| [`docs/JJSCAN_PLUS_RULES.md`](docs/JJSCAN_PLUS_RULES.md) | The detection rule library — Phase 1 must-demo and Phase 2 roadmap |
| [`docs/ABEND_PATTERN_LIBRARY.md`](docs/ABEND_PATTERN_LIBRARY.md) | Pre-seeded library of ~15 abend patterns with regex, fixes, traces |
| [`docs/CONFIDENCE_SCORE.md`](docs/CONFIDENCE_SCORE.md) | Score formula, weights, override rules, worked examples |
| [`docs/AUDIT_LOG.md`](docs/AUDIT_LOG.md) | What gets logged, retention, replay format |
| [`docs/REVIEW_QUEUE.md`](docs/REVIEW_QUEUE.md) | Cloudant change-feed → WebSocket → frontend toast flow |
| [`docs/LEARNING_LOOP.md`](docs/LEARNING_LOOP.md) | How accept/dismiss feedback trains the next-call ranking |
| [`docs/API.md`](docs/API.md) | Backend HTTP endpoints, request/response shapes |

### Setup and tooling

| File | What it answers |
|---|---|
| [`docs/KICKOFF_CHECKLIST.md`](docs/KICKOFF_CHECKLIST.md) | The literal first 60 minutes when you both sit down |
| [`docs/INSTALLATION.md`](docs/INSTALLATION.md) | Per-OS install of every dependency |
| [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md) | MCP config for Bob IDE (both) and Claude Code (Golden only) |
| [`docs/TOOLS_AND_SERVICES.md`](docs/TOOLS_AND_SERVICES.md) | Every account, free tier, library, and library version |
| [`docs/CORPUS.md`](docs/CORPUS.md) | The MeridianBank synthetic shop — sourcing, structure, fake-data rules |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | GitHub Actions for frontend (Pages) and backend (Code Engine) |

### Workflow and team

| File | What it answers |
|---|---|
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | Daily flow: session start → work → session export → end-of-day |
| [`docs/TEAM_WORKSPACE.md`](docs/TEAM_WORKSPACE.md) | Who owns what, daily sync ritual, conflict resolution |
| [`docs/BOBCOIN_BUDGET.md`](docs/BOBCOIN_BUDGET.md) | Per-feature coin allocation; when to fall back to Claude Code (Golden) |
| [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md) | The four-phase build sequence with timing and exit criteria |

### Risk and security

| File | What it answers |
|---|---|
| [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md) | What can go wrong, mitigation per item, owner |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Secrets handling, IBM Cloud credential rules, PAT scope minimization |
| [`docs/TESTING.md`](docs/TESTING.md) | Three-tier test regime: CI, demo smoke, resilience scenarios |

### Reference

| File | What it answers |
|---|---|
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | z/OS terms, JCL/COBOL/DB2 vocabulary for non-mainframe judges |
| [`docs/FAQ.md`](docs/FAQ.md) | Common questions for general visitors (judges-specific is QA_PREP) |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phase 1 (locked), Phase 2 pilot, Phase 3 commercial, Phase 4 platform |

### Templates

| File | What it answers |
|---|---|
| [`docs/templates/CLAUDE.md.template`](docs/templates/CLAUDE.md.template) | Silent-partner rules — Golden copies to `CLAUDE.md` (gitignored) |
| [`docs/templates/PR_TEMPLATE.md`](docs/templates/PR_TEMPLATE.md) | PR description format with Coins-burned line |

### Judging deliverable

| File | What it answers |
|---|---|
| [`bob_sessions/README.md`](bob_sessions/README.md) | Export instructions, folder convention |
| [`bob_sessions/golden/`](bob_sessions/golden/) | Golden's exported task histories and consumption screenshots |
| [`bob_sessions/sayan/`](bob_sessions/sayan/) | Sayan's exported task histories and consumption screenshots |

---

## What this index does NOT include

These intentionally have no doc:

- Auto-generated API client SDKs (they regenerate from the OpenAPI spec)
- Inline code documentation (lives in source comments and JSDoc/docstrings)
- Bob conversation logs (tracked in `bob_sessions/`, not under `docs/`)
- Per-feature product copy and microcopy (lives in component files)

If you find yourself needing a doc that's not in this index, **add the doc, then add the row here.** Single source of truth.

---

## Doc-writing rules

When adding a new doc:

1. Start with **what question it answers**, not what it covers. The "What it answers" column above is the test — if you can't write that single line, the doc isn't focused enough.
2. Aim for ~300–800 lines. If you're under 100, fold into another doc. If you're over 1500, split.
3. Open with a one-sentence "purpose" line.
4. End with "what's next" or a roadmap section.
5. Cross-link to related docs at first mention — readers should be able to follow the graph without going back to this index.
6. No emojis except sparing status indicators (✅ ❌).
7. No AI co-author footers, no "Generated with" lines, no Claude/Bob/Granite references in commit metadata. The work is the team's. Tools are tools.
