# Roadmap

What Helios will be after the hackathon. Not a wish list — a sequenced plan with explicit non-goals.

The hackathon ships **Phase 1**. Phases 2 and 3 are the answer when judges or recruiters ask: *"What's next?"*

---

## Phase 1 — Hackathon submission (LOCKED)

In scope:

- 3 deep features + Confidence Score wrapper
- MeridianBank synthetic corpus
- Region Atlas (7 regions, diff view, promote wizard, backup generator)
- JJSCAN+ with 4 demoed rules (copybook_drift, missing_proc_member, proc_override_conflict, db2_plan_mismatch)
- ABEND Archaeologist with ~15 seeded patterns
- Confidence Score with publishable formula and weights
- Review Queue with real-time WebSocket
- Audit log with hash chain
- Learning Loop with dissent surfacing and weight autotune
- Two-developer team workflow (Bob IDE + Git + MCP)
- Demo arc with Maya persona, two scenes
- Quantified before/after metrics

Out of scope (parked for later):

- Real LPAR integration (synthetic only)
- SSO (seeded users only)
- Multi-tenant UI (data model is multi-tenant; UI assumes one shop)
- Notification fan-out (Slack/Teams/email)
- Mobile app (responsive web only)

Phase 1 success: judges score 100% on the 20-point rubric per `docs/JUDGING_ALIGNMENT.md`.

## Phase 2 — Pilot-ready (post-hackathon, weeks 1–6)

Goal: a regulated bank could pilot Helios on a non-prod LPAR with their own data.

| Item | Why | Owner | Effort |
|---|---|---|---|
| Real Zowe integration for read-only PDS browsing | First step toward real-mainframe data | Golden | 1 wk |
| SSO via OIDC (Okta/AzureAD/Ping) | Banks won't let us bootstrap from JWT | Golden | 1 wk |
| Notification fan-out (Slack, Teams, email) | Reviewers want notifications where they live | Sayan | 4 d |
| Customer-managed encryption keys for blobs | Regulated buyer requirement | Golden | 3 d |
| Learning loop dashboard (precision/recall by rule) | Internal trust + tuning | Sayan | 4 d |
| Phase-2 JJSCAN+ rules: dead branches, GDG misalignment, restart-step incompatibility, JCL syntax-but-won't-run, circular includes | Round out the rule library | Golden | 1 wk |
| Webhook fan-out for audit events | SIEM forwarding | Golden | 2 d |
| Multi-tenant UI (shop switcher) | Make data-model multi-tenancy visible | Sayan | 3 d |
| SLA-based auto-escalation in Review Queue | Production-realistic ops | Golden | 3 d |
| Cloudant → Postgres migration (optional) | If Cloudant Lite ceases to fit | Golden | 1 wk |

Phase 2 success: a willing pilot bank runs Helios for 30 days against a real non-prod region and produces usable signal.

## Phase 3 — Commercial-ready (months 2–6)

Goal: Helios is sellable as a product to mainframe shops, alongside or atop existing tooling (Endevor, ChangeMan, etc.).

### Federation
- Cross-shop federated learning (with explicit opt-in) — rules that generalize get promoted to a community library; shop-specific signals stay private.
- Vector store (likely IBM Watsonx Discovery) for "rules that behave like this rule" semantic similarity.

### Deeper modernization
- COBOL → Java translation pilot driven by Granite Code, with the audit log capturing every translation decision.
- CICS transaction analysis (Phase 1 leaves CICS untouched).
- Db2 z/OS → Db2 LUW migration assistance.

### Ops integrations
- IBM Z OMEGAMON metrics ingestion for live job health overlay on the Confidence Score dashboard.
- Splunk / Dynatrace adapters for the audit log.

### Compliance
- SOC 2 Type II audit (Helios is the controlled environment).
- HIPAA / FedRAMP boundary documentation (pre-work, not certification).
- Cryptographic per-actor signing of audit events.
- Active write-ahead replication of audit log to a separate cloud / region.

### UX
- Mobile push notifications via APNs/FCM.
- Standalone Helios IDE plugin for ISPF (yes, ISPF — meet developers where they live).
- Voice query for ABEND triage on phone ("What broke last night?").

## Phase 4 — Platform (months 6–12)

Goal: third parties build on Helios.

- Public API + SDK (the Phase 1 API is already documented per `docs/API.md`).
- Plugin model for custom JJSCAN+ rules contributed by customers.
- Marketplace for runbook libraries (industry-specific: insurance, banking, telco).
- Helios SDK for IBM i (RPG) — same primitives, different language.

This phase converts Helios from a tool a bank uses internally to an ecosystem a bank's vendors integrate with.

## Things we will NOT do

These are tempting but out of scope, permanently:

- **Replace Endevor / ChangeMan.** Helios is an intelligence layer over those tools, not a replacement. Banks have decade-long contracts; we don't fight that.
- **Build our own LLM.** We use Granite + Claude (in Bob IDE) + open-source. We are not in the model-training business.
- **Be a generic IDE.** Bob is the IDE. Helios is a domain-specific layer Bob runs.
- **Write COBOL on behalf of users.** We summarize, trace, explain, score. We do not generate net-new business logic.
- **Migrate code without a human in the loop.** Modernization is collaborative by design; auto-translation without review violates everything Maya stands for.
- **Be cloud-or-die.** Helios will run on-prem when banks ask (Phase 2 has a containerized self-hosted path).

## How prioritization works post-hackathon

1. Pilot bank's blockers come first.
2. JJSCAN+ rules ranked by frequency-of-pain in pilot data.
3. Anything labeled `compliance` or `security` jumps the queue.
4. UI polish only after a feature has run in pilot for 14 days.

## Where to ask for changes

- Public users: GitHub Issues with template `Phase 2 ask` or `Phase 3 ask`.
- Pilot users: shared Slack channel + weekly office hours.
- Anthropic / IBM partners: direct.

## A note on commercialization

Phase 1 is Apache 2.0. Phase 2+ likely splits into an OSS core and a commercial enterprise edition (audit log enterprise features, federation, advanced compliance). The OSS core remains permissively licensed and viable on its own.

We do not promise this. The license decision lives with the contributors; for now, every line is Apache 2.

## One sentence

> Phase 1 wins the hackathon, Phase 2 earns a pilot, Phase 3 earns a logo, Phase 4 builds an ecosystem. Each phase is built on top of the prior, never as a rewrite.
