# AGENTS.md — Project Context for Bob IDE

Bob reads this file at the start of every task. Keep it concise. Do not add narrative; this is reference.

## What this project is

**Helios** — an AI control plane for IBM z/OS mainframe modernization. Turns tribal knowledge about regions, dependencies, and ABENDs into versioned, queryable, learnable artifacts. Built for IBM TechXchange Hackathon.

Four feature pillars: Region Atlas, JJSCAN+, ABEND Archaeologist, Confidence Score. Plus Review Queue (real-time team approval), Audit Log (SOX-ready), Learning Loop (shop-specific dialect adaptation).

Detail: `README.md` (start here), `docs/PROBLEM_STATEMENT.md`, `docs/DOCS_INDEX.md` (full doc map).

## Stack — locked

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11 + FastAPI + Pydantic | Auto-OpenAPI, fast dev |
| Frontend | Next.js 14 (static export) + TypeScript + Tailwind | Free hosting on Pages |
| State | IBM Cloudant Lite | Free tier, `_changes` feed, doc-oriented |
| AI | watsonx.ai (Granite Code 8B + Granite-3-8B-Instruct) | IBM hackathon, no fine-tuning |
| Realtime | Single WebSocket per user, polling fallback | Demo-resilient |
| Backend host | IBM Code Engine (scale-to-zero) | Free tier sufficient |
| Frontend host | GitHub Pages | Free, decoupled from backend |
| IDE | Bob IDE (primary) + Claude Code (Golden's silent backup) | Hackathon team workflow |
| MCP | github, filesystem, memory, fetch + 4 custom Helios servers | See `docs/MCP_SETUP.md` |

Do not introduce new dependencies without checking `docs/TOOLS_AND_SERVICES.md`.

## Team

| Person | Owns | Coin pool |
|---|---|---|
| Golden | Backend, MCP servers, IBM Cloud infra, Cloudant schema, audit writer, score engine, ABEND classifier | Bob coins + Claude Code (sidecar) |
| Sayan | Frontend, demo polish, hero shots, Maya/Anil split-screen, Monaco diff viewer, mobile-responsive review queue | Bob coins only — ration carefully |

Seams: `docs/API.md` (HTTP contract) and `docs/DATA_MODEL.md` (Cloudant schema). Treat both as sacred — no PR merges that change either without the other person reading it.

## Personas

The user is **Maya Patel** (`docs/PERSONA_MAYA.md`). Reviewer is **Anil Verma**, her director. Test the question on every feature: *"Does this make Maya's Thursday afternoon better?"* If no, cut it.

Demo shop is **MeridianBank** (`docs/CORPUS.md`). Hero JCL is `CUST_DELETE_INACTIVE.JCL`, demo arc is the 62 → 94 → 100 score progression.

## Hard rules

These are not negotiable. Bob enforces in plan mode; humans enforce in review.

1. **Never commit AI co-author trailers.** No "Generated with...", no "Co-authored-by: Bob/Claude/Granite." The work is the team's. Tools are tools.
2. **Never reference Bob/Claude/Granite in code, comments, or docs.** Same reason.
3. **Never commit `.env`, `CLAUDE.md`, or `.bob/sessions/`.** All are gitignored. Do not "fix" the exclusion.
4. **Never log secrets.** Audit log captures everything *except* secret values. The `client_meta.ip_hash` example in `docs/AUDIT_LOG.md` is the pattern.
5. **Never merge a PR that breaks `docs/API.md` or `docs/DATA_MODEL.md` without explicit cross-team review.**
6. **Backend lint rule: every state-changing endpoint must call `audit_writer.write_event`.** Enforced by `tools/lint_audit_calls.py` in CI.
7. **Frontend rule: every Granite-generated text must be visibly attributed as a suggestion, never as fact.**

## Common Bob tasks for this project

When asked to "implement X," Bob's first move is to identify which doc specifies X and re-read it. The specs are deliberately detailed; Bob's job is to translate spec → code, not to invent.

| Task type | Read first | Expected output |
|---|---|---|
| New API endpoint | `docs/API.md` (find the section) + `docs/DATA_MODEL.md` | FastAPI route + Pydantic models + audit_writer call + pytest |
| New JJSCAN+ rule | `docs/JJSCAN_PLUS_RULES.md` + corpus seeded defects | Rule class + golden test + finding doc |
| New UI component | `docs/REVIEW_QUEUE.md` or relevant feature doc + Tailwind tokens | Component + storybook entry + Playwright e2e |
| ABEND pattern | `docs/ABEND_PATTERN_LIBRARY.md` | Pattern entry + runbook seed + test fixture |
| Confidence weight tuning | `docs/CONFIDENCE_SCORE.md` + `docs/LEARNING_LOOP.md` | Region override + audit event |

## Bob mode defaults

Set in Bob's settings, not per-session:

- Mode: **Plan** (always plan before acting)
- Auto-approve: Read ✓, Write ✓, Question ✗, Execute ✗, MCP ✓ (alwaysAllow list only)
- Code completion: **OFF** (saves coins on every keystroke)
- Memory MCP: enabled for cross-session continuity

If Bob asks a clarifying question, the answer often lives in `docs/`. Search there before answering.

## Where to read more

- `README.md` — pitch + repo layout
- `docs/DOCS_INDEX.md` — every doc, by role and category
- `docs/PHASE_PLAN.md` — what to build in what order
- `docs/WORKFLOW.md` — daily ritual
- `docs/MCP_SETUP.md` — MCP server config
- `docs/BOBCOIN_BUDGET.md` — coin discipline
- `docs/TESTING.md` — what "done" means

## What this file is NOT

- Not the demo script (that's `docs/DEMO_SCRIPT.md`).
- Not the architecture diagram (that's `docs/ARCHITECTURE.md`).
- Not the API contract (that's `docs/API.md`).
- Not a changelog (that's `CHANGELOG.md`).

Keep this file under 200 lines. Bob reads it constantly; verbose costs coins.
