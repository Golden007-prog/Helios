# Judging Alignment

The hackathon rubric is **20 points**: 5 each for Completeness & Feasibility, Creativity & Innovation, Design & Usability, Effectiveness & Efficiency. This doc maps every Helios feature to the criterion it scores against and lists the artefacts judges will see.

---

## Completeness & feasibility (5 points)

> *"How feasible is the solution? How fully has the idea been thought-out and planned? How complete is the proof-of-concept submitted? How clear is the application of IBM technology?"*

| What we deliver | Where to see it |
|---|---|
| Full architecture diagram with every component named and connected | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — Mermaid SAD + sequence diagram |
| Feature-by-feature spec with input/output contracts | [`docs/SPECS.md`](SPECS.md) |
| Working frontend deployed to GitHub Pages, working backend on Code Engine | Live URLs in the README |
| Bob session reports for every task in `bob_sessions/golden/` and `bob_sessions/sayan/` | required for judging — the audit trail |
| IBM tech mapped explicitly per module: Bob IDE, watsonx.ai (Granite Code 8B), watsonx Orchestrate, Cloudant Lite, Code Engine, NLU | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) §"Component breakdown" + §"IBM Cloud Services" |
| Demo runs end-to-end on the MeridianBank synthetic corpus — no missing pieces, no "this would work in production" hand-waves | [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md) |
| Three deep features fully built, not five half-built ones | by design — see [`SPECS.md`](SPECS.md) "Out of scope" section for what we intentionally cut |

**Why we score well here:** judges instantly see scope discipline. We picked three features and shipped them excellently, not thirteen and shipped them badly. The IBM tech callouts are explicit per module, not vague.

---

## Creativity & innovation (5 points)

> *"How unique and original was the approach in applying AI technology to address the stated issue? Is the solution differentiated in the market?"*

| What sets us apart | Why it's original |
|---|---|
| **Region Atlas as a versioned artifact** | Every shop has tribal region knowledge in a wiki. Nobody has built it as a structured, queryable, diff-able YAML model with a promote-job wizard. This is genuinely new. |
| **Pre-flight Backup Generator** | Auto-generated UNLOAD + IMAGE COPY (DB2) or IDCAMS REPRO (VSAM) bound to target region context, triggered by destructive operations on tracked resources. No tool does this today. |
| **JJSCAN+ as a depth upgrade to `jjscan`** | Naming positions us against the tool every Z dev knows; the depth (copybook drift, PROC override conflict, plan-vs-bound-collection mismatch) is what makes a senior dev say "finally". |
| **ABEND Archaeologist's COBOL business-rule traceback** | Pattern-library + Granite Code on the source COBOL turns the senior dev's mental walk into a 30-second explanation any junior can act on. Other ABEND tools stop at "S0C7 in CUSTPROC line 247" — we explain *what business rule broke and why*. |
| **Confidence Score as a single auditable number** | Composite metric every reviewer can quote in their write-up. Auditable formula, configurable weights, override-with-reason. SOX-ready out of the box. |
| **Real-time Review Queue** | Two-developer team becomes the unfair advantage — we demo split-screen collaboration with WebSocket toasts. |
| **Learning loop** | Every accept/dismiss on a JJSCAN+ finding feeds Cloudant; future scans surface team-specific dismissal rates. *"3 of 4 prior teams dismissed this finding as false positive on similar jobs."* |

**Why we score well here:** the Region Atlas + Pre-flight Backup combo is unmistakably new. JJSCAN+'s extra detection rules are mainframe-specific in a way generic AI coding tools can't replicate.

---

## Design & usability (5 points)

> *"How good is the design, user experience, and ease-of-use of the solution? How quickly and easily could it be put to use in real-world scenarios and adopted by target users?"*

| What we deliver | Why it works |
|---|---|
| **One dashboard, four tabs** (Studio / Atlas / Archaeology / Audit) | Mental model is obvious. No menu archaeology. |
| **Three hero frames** designed for screenshot-worthy impact (Region Atlas diff, Confidence Score gauge, ABEND three-pane) | [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md) §"Hero shots" |
| **Monaco editor** with custom JCL/COBOL syntax | Looks like the tools mainframe devs already use; instant familiarity |
| **Dark mode default**, accessible color contrast, keyboard shortcuts that match VS Code | enterprise-grade polish |
| **Region picker as a dropdown**, not free text | Eliminates typo-class errors |
| **Helios Confidence Score as the headline number** | Reviewers want one number to drill in from. We give them one. |
| **Real-time Review Queue with WebSocket toasts** | Feels alive, not like a form-fill app |
| **Audit log viewer with CSV export** | Compliance teams adopt fastest when their tools work |

**Why we score well here:** we're not designing for a hackathon judge — we're designing for a senior mainframe developer at a Fortune 500 bank. That bar is higher and shows.

---

## Effectiveness & efficiency (5 points)

> *"Does the solution address a high priority and relevant issue within the hackathon theme? Does it achieve its goal effectively and efficiently? Can it achieve a measurable impact in the field? Does it have potential to scale to more users or use cases?"*

### Priority and relevance

The hackathon theme is *"App modernization. Reverse-engineer undocumented code and execute validated upgrades in days instead of months."* Helios attacks three of the most expensive moments in mainframe modernization: region promotion, dependency analysis, and ABEND triage. Every Fortune 500 bank, insurer, airline, and government agency on z/OS has these pains. The market is enormous.

### Measurable impact

Quantified targets we'll publish in the README the morning of submission:

| Workflow | Manual baseline | With Helios | Source |
|---|---|---|---|
| JCL promotion int2 → int3 | 47 min average | 6 min target | timed runs on MeridianBank |
| ABEND root cause identification | 4.3 hr average | 4 min target | ten seeded incidents in the corpus |
| First-prod-run ABEND rate after promotion | 18% baseline | 0% target | ten promotions, scored before vs. after |

We produce these numbers credibly with the synthetic shop in a single afternoon of timed runs.

### Scale to more users / use cases

| Dimension | Helios design |
|---|---|
| **Multi-tenant by region** | Every operation scoped to a region profile; new region = new YAML file |
| **Multi-tenant by shop** | Cloudant database per customer; YAML region profiles are inherently portable |
| **On-prem deployment** | FastAPI backend runs in any container runtime; Cloudant has on-prem equivalent (CouchDB); inference can swap to local Granite via Ollama |
| **LDAP / SSO integration** | Pluggable auth at the FastAPI gateway; not built for hackathon but architected in |
| **RACF integration** | Region profiles already model RACF groups; future runtime integration straightforward |
| **Audit & compliance** | SOX-ready audit log from day one |

**Why we score well here:** the impact metrics are concrete (minutes, percentages) and the scale story is structural — Helios is built so a different bank can drop in their own region profiles tomorrow.

---

## IBM technology callouts per feature

The hackathon explicitly requires showcasing IBM Bob IDE as a core component. We go further by mapping every feature to specific IBM tech:

| Feature | IBM tech used | How |
|---|---|---|
| **Region Atlas** | Bob IDE Skills + Custom Modes | `.bob/skills/promote-job/SKILL.md`, `add-region`, `diff-regions` are reusable team workflows |
| **Region Atlas → Cloudant** | Cloudant Lite | All region profiles stored as JSON docs; change feed powers Review Queue |
| **JJSCAN+** | Bob IDE MCP integration + watsonx.ai | Custom `helios-corpus` MCP gives Bob direct corpus access; Granite Code explains drift |
| **JJSCAN+ rule engine** | Code Engine | Stateless FastAPI service deployed serverlessly |
| **ABEND Archaeologist** | watsonx.ai Granite Code 8B + IBM NLU | Granite for COBOL business-rule explanation; NLU for entity extraction from dumps |
| **ABEND learning loop** | Cloudant + watsonx Orchestrate | Past resolutions stored in Cloudant; Orchestrate routes the diagnose-then-explain flow |
| **Confidence Score** | Code Engine + Bob IDE Code Reviews | Score computed by backend; surfaced via Bob's PR review integration |
| **Audit Log** | Cloudant change feed | Append-only writes; queryable via Cloudant API |
| **Review Queue** | Cloudant change feed + WebSockets | Real-time without extra infra |
| **Multi-agent orchestration** | watsonx Orchestrate | Atlas / JJSCAN+ / ABEND / Score modeled as collaborator agents |

---

## What's in `bob_sessions/` for the judges

Required submission deliverable. Each task report includes:

- The full conversation between the developer and Bob
- The consumption summary (Context Length, Task ID, Tokens, Cache, API Cost, Size)
- Screenshot of the consumption summary as PNG

Folder structure on submission day:

```
bob_sessions/
├── golden/
│   ├── 01-phase1-foundation.md           + 01-phase1-foundation-summary.png
│   ├── 02-region-atlas-schema.md         + .png
│   ├── 03-cloudant-mcp-server.md         + .png
│   ├── 04-jjscan-plus-rules.md           + .png
│   ├── 05-abend-pattern-library.md       + .png
│   ├── 06-confidence-score-engine.md     + .png
│   └── 07-deploy-code-engine.md          + .png
└── sayan/
    ├── 01-frontend-skeleton.md           + .png
    ├── 02-monaco-jcl-syntax.md           + .png
    ├── 03-region-atlas-diff-ui.md        + .png
    ├── 04-confidence-score-gauge.md      + .png
    ├── 05-abend-three-pane-view.md       + .png
    ├── 06-review-queue-websocket.md      + .png
    └── 07-demo-polish.md                 + .png
```

Required as part of the project submission per the IBM hackathon guide.

---

## The non-Z judge paragraph

Most judges won't be mainframe developers. The README must give them a paragraph they can quote in deliberations:

> *"Roughly $3 trillion of enterprise transactions flow through z/OS daily. The talent pool to maintain these systems shrinks every year. Helios isn't migration-or-die — it's a working bridge between the developers who built these systems and the ones who'll inherit them. Every Fortune 500 bank, insurer, airline, and government agency on z/OS faces this exact problem. We've shipped a control plane that demonstrably saves hours per promotion, prevents production ABENDs before they happen, and turns ABEND triage from senior-developer folklore into a 30-second guided diagnosis."*

This is the line the non-Z judge uses to defend our score in deliberations. Worth memorizing.

---

## Final pre-submission checklist

- [ ] All three features demonstrably work in the live environment
- [ ] Quantified before/after numbers in README (timed against the corpus)
- [ ] All Bob session reports exported and committed
- [ ] Hero shots polished (Region Atlas diff, Confidence Score gauge, ABEND three-pane)
- [ ] 90-second demo video recorded as fallback
- [ ] README has "for non-Z judges" paragraph
- [ ] Architecture diagram renders cleanly in GitHub
- [ ] Live URLs (frontend GH Pages + backend Code Engine) listed in README
- [ ] Tag the submission: `git tag v1.0-hackathon && git push --tags`
