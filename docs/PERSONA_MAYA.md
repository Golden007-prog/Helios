# Persona — Maya Patel, Mainframe Developer at MeridianBank

This document defines the demo persona who anchors the entire Helios narrative. Every screen, every feature, every claim should be inspectable through Maya's lens. If a feature does not solve a problem Maya has on a Thursday afternoon, it does not ship.

---

## Profile

| Field | Value |
|---|---|
| Name | Maya Patel |
| Age | 34 |
| Title | Senior Mainframe Developer |
| Employer | MeridianBank (synthetic — built on GnuCOBOL test suite + opensourcecobol/Bankdemo) |
| Years on z/OS | 9 |
| Years at MeridianBank | 4 |
| Reports to | Anil Verma, Director of Core Banking Platforms |
| Team size | 6 mainframe devs, 2 ops, 1 SRE-on-loan-from-cloud |
| Primary languages | Enterprise COBOL 6.3, JCL, REXX (some) |
| Tools today | ISPF, File-Aid, Endevor, Fault Analyzer, Slack, Git via Zowe |
| Tools tomorrow | Bob IDE + Helios (the bridge) |

## Daily reality

Maya owns the **customer master subsystem** — the heart of MeridianBank's retail banking platform. Roughly 280 COBOL programs, 90 copybooks, 140 JCL members, 12 DB2 plans, 4 VSAM clusters. She is the only person on her team who fully understands the dependency graph; her colleague Raj is getting there but still asks her for context daily.

Her week splits into rough thirds:

- **Build** — net-new features for product asks (e.g., "support joint accounts with three holders").
- **Promote** — moving tested code through the four pre-prod regions (`int1` → `int2` → `int3` → `prod`) with parameter substitutions, BIND tweaks, schedule wiring. The slowest, most error-prone third.
- **Fight fires** — responding to ABENDs, mostly in the small hours of Saturday morning when the batch window runs.

She is not a Luddite. She has a personal Mac with VS Code, contributes to a Python library on GitHub on weekends, and has been quietly reading the Bob IDE docs since IBM TechXchange announced it.

## Pains, ranked

1. **Region tribal knowledge lives in three Confluence pages, four Slack threads, and her head.** Every new region added in the last 18 months took her 2–3 days to onboard for the team because the differences were nowhere written down. Helios Region Atlas exists for this.

2. **Promotions are 47 minutes of hand-editing then 4 hours of waiting to find out if she got it right.** If she missed a STEPLIB swap or forgot the new DB2 subsystem ID, prod ABENDs at 2 a.m. and she gets paged. JJSCAN+ and the Confidence Score exist for this.

3. **ABEND triage starts with grep on 12,000-line SYSLOGs.** When she finally finds the failing step, she has to remember that the same S0C7 hit two months ago and someone fixed it — but where's that fix? The Slack thread is buried, the Confluence page was never written. ABEND Archaeologist + the Runbook Generator exist for this.

4. **Approvals are a bottleneck.** When she promotes to `prod`, Anil has to sign off. He's in meetings 6 hours a day. The Review Queue exists for this — she promotes, Anil sees the diff and the score on his phone, taps Approve, done.

5. **Audit asks happen quarterly.** "Who changed the int3 BIND parameters between Jan 14 and Feb 2?" Today: she greps Endevor logs and three Slack channels for half a day. With Helios audit log: one query.

## What Maya does NOT want

- Another tool that requires her to leave ISPF for trivial tasks. Helios must work alongside her existing flow, not replace it.
- A black-box AI that "just trusts me." She is responsible if prod breaks; she needs to see the reasoning and override it.
- More dashboards. She has six already. Helios is one screen with one number (the Confidence Score) and a drill-down when she wants it.

## Demo arc — Thursday, October 23, 4:12 p.m.

### Scene 1 — The promote (60 seconds)

Maya needs to promote `CUST_DELETE_INACTIVE.JCL` from `int2` → `int3` before EOD. The job runs nightly from `int3` to drop dormant accounts older than 7 years. She opens Bob IDE, opens the JCL, clicks the Helios badge in the gutter.

> **Helios sidebar:** *"Promote `CUST_DELETE_INACTIVE.JCL` from `int2` to `int3`?"*
>
> She clicks Promote.
>
> Region Atlas runs the substitutions. 7 fields change. Each is highlighted in the diff with a hover-over reason:
> - `STEPLIB DSN` int2 → int3
> - `DSN SYSTEM(DBI2)` → `DSN SYSTEM(DBI3)`
> - `JOBCARD` class A → class P (prod-like, longer runtime allowed)
> - `HLQ` `CUST.INT2.*` → `CUST.INT3.*`
> - `BIND PACKAGE` `CUSTPKG.INT2` → `CUSTPKG.INT3`
> - `RACF group` `INT2DEV` → `INT3DEV`
> - `SYSOUT class` X → S
>
> Confidence Score appears: **62 / 100 — RED**.
>
> Top 3 reasons:
> 1. `CUST.MASTER` is a protected resource in `int3`; no paired backup job staged. (-30)
> 2. Copybook `CUSTREC` has drifted: `int2` uses v3.1, `int3` SYSLIB still pinned to v2.7. (-5)
> 3. Last 30 days: 3 historical ABENDs on similar `DELETE_INACTIVE` patterns in this region. (-3)

She clicks **Auto-fix the backup gap**. Helios drops in a paired `UNLOAD + IMAGE COPY` job named `CUST.INT3.BKP.D26296.T161203` with 30-day retention. Score jumps to **94 / GREEN**.

She clicks the copybook drift finding. JJSCAN+ shows the two versions side-by-side. The fix is to update the SYSLIB concatenation order so `int3` resolves to v3.1. One click. Score: **100 / GREEN**.

She clicks **Promote**. Two things happen:
- The promoted JCL lands in the `int3` PDS.
- A toast pops up on Anil's phone: *"Maya promoted CUST_DELETE_INACTIVE to int3, score 100, awaiting your review."*

Anil taps **Approve** mid-meeting. Promotion is committed. Audit log row written. Time elapsed: **6 minutes**. Maya leaves at 5.

### Scene 2 — The ABEND, three weeks later (30 seconds)

It's a Tuesday morning. The job ABENDed overnight with `S0C7`. The on-call dev pasted the SYSLOG into Slack at 3 a.m. and went back to bed. Maya opens Helios.

She pastes the same SYSLOG into ABEND Archaeologist. Three panes:

- **Left:** the SYSLOG, the failing line highlighted (`IGZ0035S` at offset `+0x1A4` in `CUSTPROC`).
- **Center:** the COBOL source, line 247 highlighted: `COMPUTE WS-CUST-AGE = FUNCTION INTEGER-OF-DATE(CURRENT-DATE) - WS-CUST-DOB-INT`.
- **Right:** the business rule explanation generated by Granite Code — *"`WS-CUST-DOB-INT` was set in paragraph `2300-CALC-RETIREMENT` from `CUST.MASTER` row read at offset 14782. That row's `DOB` field is `NULL` — likely from the failed `BATCH_IMPORT_001` on Oct 12 that left 3 partial rows."*

Below: a runbook entry from a similar incident in `int1` last quarter, with the SQL fix Raj wrote to identify and quarantine the bad rows. Below that: a one-click **Apply quarantine SQL** button.

Triage time: **4 minutes**. The team's runbook gets a new entry automatically.

---

## What Maya tells her partner that night

> *"We got a new tool today. The annoying promotion thing I do every week — it took six minutes instead of three hours. And we caught the missing backup before it ate prod. I think Anil is going to want to roll it out across all four product teams."*

That sentence is the entire pitch for Helios. If a judge can imagine Maya saying it, Helios wins.

---

## Composite — who Maya is built from

Maya is a composite drawn from three real archetypes the team has worked with or studied:

- The **9-year COBOL veteran** who is bilingual in mainframe and modern stacks but resentful that no tool respects both worlds.
- The **single-point-of-failure expert** that every shop has — the person whose vacation triggers low-grade panic.
- The **bridge-builder** — someone who actively wants to mentor the next generation but lacks the artifacts to do it (region docs, runbooks, dependency graphs).

Helios serves all three by turning her tribal knowledge into versioned, queryable, learnable artifacts.

## Where Maya appears in the codebase

- `shared/sample-corpus/MERIDIANBANK/` — her synthetic shop
- `docs/DEMO_SCRIPT.md` — Scenes 1 and 2 above, beat-by-beat
- `docs/CORPUS.md` — what's in MeridianBank, file by file
- `docs/REVIEW_QUEUE.md` — Anil's mobile approval flow
- `docs/AUDIT_LOG.md` — the row written when she promotes

When in doubt about a design decision, ask: *"Does this make Maya's Thursday afternoon better?"* If no, cut it.
