# FAQ

Common questions from people first encountering Helios. For judge-specific Q&A, see `docs/QA_PREP.md`.

---

## What is Helios in one sentence?

An AI control plane for z/OS mainframe modernization that turns tribal knowledge about regions, dependencies, and ABENDs into versioned, queryable, learnable artifacts.

## Who is it for?

Mainframe developers like Maya (see `docs/PERSONA_MAYA.md`) and the team leads who approve their work. Specifically: shops with COBOL + JCL + DB2 + multiple regions where promotions today are slow, error-prone, and undocumented.

## Is this a mainframe replacement?

No. Helios runs *alongside* the mainframe and existing tooling (Endevor, ChangeMan, ISPF). It captures and operates on metadata about mainframe artifacts; it doesn't run COBOL, replace JES, or migrate workloads. The mainframe stays where it is — modernization is collaborative.

## Will it migrate my COBOL to Java?

Not in Phase 1. Phase 3 includes a Granite-Code-driven COBOL→Java translation pilot with the audit log capturing every translation decision (`docs/ROADMAP.md`). Until then, Helios reads, summarizes, traces, and explains — it does not rewrite business logic.

## Why "Helios"?

Greek for sun. Mainframes are the dark stars of enterprise software — massive, hot, illuminating everything around them, but you can't look at them directly. Helios is the lens that lets you actually see what's there.

## Why do you need an AI for this? Couldn't you write rules?

For Region Atlas substitutions and many JJSCAN+ rules: yes, you could write deterministic rules. We do — most of JJSCAN+ is plain static analysis. But three feature surfaces genuinely benefit from a language model:

1. **Granite Code summarization of COBOL paragraphs and PROCs** — explaining business rules in plain English from undocumented code is the hackathon's stated theme.
2. **ABEND root cause explanation** — generating the natural-language fix description from a SYSLOG paste.
3. **Region substitution reasoning** — explaining *why* a parameter changed, not just what changed.

Where rules suffice, we use rules. We don't reach for an LLM for cosmetic effect.

## Why Cloudant and not Postgres?

Document-shaped data with wildly varying schemas (audit events especially), free Lite tier sufficient for the demo, native `_changes` feed that powers the Review Queue's real-time delivery, and IBM-native (which scores well at an IBM hackathon). Trade-offs discussed in `docs/DATA_MODEL.md` §14.

## Why FastAPI and not Spring?

Backend dev (Golden) is fastest in Python; the API is small enough that framework choice doesn't affect outcome; FastAPI's auto-OpenAPI + Pydantic validation are faster than equivalent Spring boilerplate. If a customer wants Java, the API contract is documented and reimplementable.

## Why Next.js static + GitHub Pages and not Code Engine for the frontend?

Frontend is fully static (no SSR needed), GitHub Pages is free, and routing the UI separately from the backend means a full backend outage doesn't take the marketing site down with it. The backend lives in Code Engine for the WebSocket and the watsonx calls.

## Is this open source?

Yes — Apache 2.0 (`LICENSE`). Phase 1 is fully open. Phase 2+ may split into an OSS core and a commercial enterprise edition; the core stays permissive (`docs/ROADMAP.md`).

## Where does the data come from in the demo?

A synthetic shop called MeridianBank, assembled from the GnuCOBOL test suite, opensourcecobol/Bankdemo, and the NIST COBOL85 conformance suite, with renamed headers and stitched-together JCL/DB2/copybooks. Full spec in `docs/CORPUS.md`. No real bank's code is used.

## Can I run it without an IBM Cloud account?

Yes, in mock mode for development — see `docs/INSTALLATION.md` §10. Cloudant is replaced by local CouchDB, watsonx by canned responses. The demo is identical pixel-for-pixel because every Granite response in the demo is also pre-recorded.

## What if my mainframe shop has 20 regions, not 7?

Region Atlas scales to N regions linearly. The diff view supports any pair. The 7 in MeridianBank are illustrative; the schema (`docs/REGION_PROFILE_SCHEMA.md`) and indexes (`docs/DATA_MODEL.md`) impose no upper bound.

## What's the cost story?

Phase 1 / hackathon: $0 out-of-pocket — IBM Cloud free trial credits + Lite tiers + GitHub Pages + 80 Bobcoins from the team. Forecast in `docs/TOOLS_AND_SERVICES.md` and `docs/BOBCOIN_BUDGET.md`.

Phase 2 pilot: roughly $200–500/month per shop in IBM Cloud charges, scaling with audit log volume.

Phase 3 commercial: priced per shop / per developer seat, TBD based on pilot signal.

## Is the audit log actually compliant?

Hash-chained, append-only, RFC-8785 canonicalized, queryable, exportable. Sufficient for SOX evidence today. Not yet certified to SOC 2 Type II — that's Phase 3 (`docs/ROADMAP.md`). Full discussion in `docs/AUDIT_LOG.md`.

## How does the Confidence Score actually work?

Published formula: `100 - Σ(jjscan × severity_weight) - region_mismatch - backup_gap - historical_abend + spec_match_bonus`, with default weights and per-region overrides. Worked examples A–D in `docs/CONFIDENCE_SCORE.md`. Not a black box.

## Can I trust an AI to grade my JCL?

The score is deterministic from the inputs (rules, weights, prior outcomes) and every component is shown to the user. The AI portion is the explanation layer (Granite Code summarizing why something matters), not the math. You can audit any score's derivation; you can override any score with a recorded reason; weights are configurable per region. Trust is built on visibility, not on declaration.

## What if the AI is wrong?

Two safeguards:

1. **Every AI output is presented as a suggestion, never as a fait accompli.** The developer always has the final click.
2. **The Learning Loop captures dissent.** When you override or dismiss, that signal trains future surfacing — Helios learns when to be quieter.

Plus the Review Queue: nothing protected ships without a human reviewer who is not the initiator.

## Why do you only support 4 JJSCAN+ rules at launch?

Depth over breadth. Five hand-tuned rules with auto-fix and dissent surfacing beat fifteen shallow ones that pattern-match poorly. The remaining rules (dead branches, GDG misalignment, restart-step incompatibility, JCL-syntax-but-won't-run, circular includes) are Phase 2 (`docs/ROADMAP.md`).

## Is this Bob-only?

Bob is the primary IDE and the recommended dev experience — the `.bob/skills/` capture our workflows as native Bob primitives. But Helios is also reachable from any HTTP client; the API (`docs/API.md`) is the contract. Phase 3 includes a standalone ISPF plugin for developers who never leave the green screen.

## What's the difference between Helios and watsonx Orchestrate?

Orchestrate is the multi-agent runtime; Helios is the product built on top of it. Orchestrate handles agent routing and tool invocation; Helios provides the four agents (Region Atlas, JJSCAN+, ABEND Archaeologist, Confidence Score) and all the domain knowledge.

## How do you avoid hallucinations?

Three layers:

1. **Grounding.** Granite Code summaries are always anchored to specific source files and line numbers via retrieval; we don't ask the model to invent.
2. **Structured output.** Where the answer must be machine-actionable (e.g., the Confidence Score breakdown, ABEND identification), we constrain the response shape and validate it.
3. **Visible provenance.** Every AI output shows the inputs that produced it, so a developer can spot when a summary is off-base.

## Who runs Helios? You? IBM?

For the hackathon: the contributors (Golden + Sayan). Post-hackathon: depends on adoption — likely a small commercial entity or a partnership with an IBM ecosystem company. The OSS core has no single owner.

## How do I contribute?

`CONTRIBUTING.md` in the repo root. PR template in `docs/templates/PR_TEMPLATE.md`. Phase 2 issues will be tagged `good-first-issue` for community contributors after the hackathon.

## How do I report a security issue?

`docs/SECURITY.md`. Do not file public issues for security reports.

## Does Helios collect any telemetry?

No usage telemetry leaves your installation. Audit log + learning signals are stored in your Cloudant; nothing is phoned home. (Phase 3's federated learning will be explicit opt-in.)

## What if our shop already has Endevor?

Helios complements Endevor — it does not replace it. Endevor manages source control and approval workflows; Helios provides the intelligence (region awareness, dependency analysis, ABEND triage, Confidence Score) that Endevor lacks. Many integrations are possible; see `docs/ROADMAP.md` Phase 3.

## Is this a wrapper around Bob?

No. Bob is the developer's IDE. Helios is the product the developer uses. Bob is to Helios what VS Code is to a web app you're building in VS Code — necessary for development, invisible to the end user.

## What about z/OS Connect, Wazi, Ansible for Z?

All complementary, all integrable. Phase 2 includes an Ansible-for-Z module so Helios-approved promotions can flow through Ansible playbooks; Phase 3 includes z/OS Connect API publishing for Helios state. We are additive to the IBM Z modernization stack, not competitive with it.

## Where is the demo video?

Recorded morning-of and uploaded to the README's top section. Don't ask for a script — read `docs/DEMO_SCRIPT.md` and `docs/PERSONA_MAYA.md` instead; they're better than any video.

## Anything else I should read first?

In order:

1. `README.md` — 2 minutes
2. `docs/PROBLEM_STATEMENT.md` — 3 minutes
3. `docs/PERSONA_MAYA.md` — 5 minutes
4. `docs/DEMO_SCRIPT.md` — 4 minutes
5. `docs/GLOSSARY.md` if mainframe terms are unfamiliar — 5 minutes

Total under 20 minutes and you'll know more about Helios than 90% of the audience.
