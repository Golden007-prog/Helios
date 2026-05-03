# Helios

> **The AI control plane for z/OS modernization.**
> Promote JCL between regions in minutes, not hours. Catch ABENDs before they ship. Ship audit-ready changes with one number every reviewer trusts.

Built for the **IBM Bob Dev Day Hackathon** — focus area: *App modernization (Java, COBOL, RPG, mainframe). Reverse-engineer undocumented code and execute validated upgrades in days instead of months.*

---

## The 30-second pitch

Mainframe shops still ship batch jobs the way they did in 1995: copy a JCL, edit by hand, hope the target region's DB2 subsystem hasn't changed since last quarter, run it Friday at 4pm, and pray nothing wakes the on-call at 2am. Tribal knowledge lives in wikis nobody reads. ABEND triage takes hours because the dev who wrote the program retired in 2019.

**Helios** turns the worst three pain points into one product surface:

1. **Region Atlas** — version-controlled YAML region profiles. Promote a JCL between regions and Helios rewrites every region-specific parameter with reasoning. Auto-generates paired backup jobs when the change touches protected data.
2. **JJSCAN+** — the dependency scanner `jjscan` should have been. Resolves every PROC, COPYBOOK, and CCLIB across SYSLIB concatenation order, then catches what `jjscan` won't: copybook drift, PROC override conflicts, plan-vs-bound-collection mismatches, GDG version misalignment, restart-step incompatibility.
3. **ABEND Archaeologist** — paste any SYSLOG, JESYSMSG, CEEDUMP, or SVC dump. Helios identifies the abend code, traces the failing instruction back to source COBOL, and explains the business rule that broke. Cross-references the team's prior resolutions.

All three feed into a single **Confidence Score** (0–100) attached to every change. Green ships, red blocks, every reason auditable.

---

## Demo: meet Maya

Open [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the 90-second story we run on judging day. *Maya, mainframe dev at MeridianBank. Thursday 4pm. Risky promotion. Goes home at 5 instead of being paged at 9.*

---

## Tech stack at a glance

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 static export → **GitHub Pages** | Free, fast, no infra |
| Backend | FastAPI on **IBM Code Engine** | Scales to zero; free tier covers hackathon |
| Datastore | **IBM Cloudant Lite** | JSON-native, free, change-feed for Review Queue |
| Inference | **watsonx.ai Granite Code 8B** + Granite-3-8B-Instruct | Strong COBOL reasoning; banned-list compliant |
| Multi-agent | **watsonx Orchestrate** | Atlas / JJSCAN+ / ABEND / Score as collaborator agents |
| Build copilot | **IBM Bob IDE** (visible) + Claude Code (silent backup, Golden only) | Bob session reports are the judging evidence |
| Sample corpus | **MeridianBank synthetic shop** | Built from GnuCOBOL test suite + opensourcecobol/Bankdemo, rebadged |

Full stack rationale and component diagram in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Repo layout

```
Helios/
├── frontend/           Sayan owns — Next.js, Monaco, React Flow, GitHub Pages CI
├── backend/            Golden owns — FastAPI, Code Engine deployment
├── mcp-servers/        Golden owns — custom MCP servers (cloudant, watsonx, corpus, ibm-cloud)
├── shared/
│   ├── prompts/        Granite Code prompt templates
│   ├── schemas/        Region profile, audit log, learning entry JSON schemas
│   └── sample-corpus/  MeridianBank synthetic shop (read-only fixtures)
├── docs/               All design docs and specs
├── bob_sessions/
│   ├── golden/         Golden's exported Bob task reports
│   └── sayan/          Sayan's exported Bob task reports
├── .bob/
│   └── mcp.json        Shared project-level MCP config (committed)
├── AGENTS.md           Project context for Bob IDE (committed)
├── CONTRIBUTING.md     Branch + PR rules
├── README.md           This file
└── .gitignore          Secrets, .claude/, build artefacts
```

Ownership rule: unless explicitly pairing, never edit the other person's top-level directory. Full conflict-avoidance protocol in [`docs/TEAM_WORKSPACE.md`](docs/TEAM_WORKSPACE.md).

---

## Quickstart

Both team members:

```bash
git clone https://github.com/Golden007-prog/Helios.git
cd Helios
cp .env.example .env        # fill in IBM Cloud + GitHub PAT — do NOT commit
```

Then install Bob IDE per [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md), confirm the project-level MCP config loaded green, and pick up your branch.

---

## Documentation map

**Strategy and judging**
- [`docs/PROBLEM_STATEMENT.md`](docs/PROBLEM_STATEMENT.md) — the mainframe modernization pain we're attacking
- [`docs/JUDGING_ALIGNMENT.md`](docs/JUDGING_ALIGNMENT.md) — how every feature maps to the four scoring criteria
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — the Maya scenario, scene by scene
- [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md) — what can go wrong, what we'll do

**Architecture and specs**
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System Architecture Diagram, data flow, deployment topology
- [`docs/SPECS.md`](docs/SPECS.md) — feature-by-feature specification (Region Atlas, JJSCAN+, ABEND Archaeologist, Confidence Score)
- [`docs/CONFIDENCE_SCORE.md`](docs/CONFIDENCE_SCORE.md) — the scoring formula, weights, override rules

**Tooling and workflow**
- [`docs/TOOLS_AND_SERVICES.md`](docs/TOOLS_AND_SERVICES.md) — every account, library, and free tier in use
- [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md) — MCP server config for Bob IDE and (Golden only) Claude Code
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — daily dev flow, Git, Bob session export
- [`docs/TEAM_WORKSPACE.md`](docs/TEAM_WORKSPACE.md) — two-developer parallel work, ownership boundaries
- [`docs/BOBCOIN_BUDGET.md`](docs/BOBCOIN_BUDGET.md) — how the 40 Bobcoins are spent per person and where Claude Code fills gaps
- [`docs/SECURITY.md`](docs/SECURITY.md) — secrets, IBM Cloud credential rules, audit

**For Bob and Claude Code**
- [`AGENTS.md`](AGENTS.md) — project context Bob IDE reads on every task
- [`docs/templates/CLAUDE.md.template`](docs/templates/CLAUDE.md.template) — Claude Code rules (Golden copies to `CLAUDE.md`, gitignored)

**For judging deliverable**
- [`bob_sessions/README.md`](bob_sessions/README.md) — how each of us exports task reports

---

## Team

| | GitHub | Owns |
|---|---|---|
| Golden (Oikantik Basu) | [@Golden007-prog](https://github.com/Golden007-prog) | Backend, MCP servers, Atlas + Sentry modules |
| Sayan | [@Sayan1320](https://github.com/Sayan1320) | Frontend, Studio + Forge UI, demo polish |

---

## License

Apache 2.0 — built for the IBM Bob Dev Day Hackathon, intended for open-source release after the event so any mainframe shop can adopt it.
