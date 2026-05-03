# Demo Script — Meet Maya

The 90-second story we run on judging day. Every feature appears in service of one continuous scenario. Judges remember stories, not feature matrices.

---

## Persona

**Maya, mainframe developer at MeridianBank.** Six years on the team. She knows COBOL well, JCL grudgingly, and the politics of Friday afternoon promotions intimately.

**Raj, her tech lead.** Approves promotions before they hit production. He's also responsible for the on-call rotation — every preventable production ABEND is one more 2am page.

**MeridianBank.** Mid-sized retail bank. Six environments: dev1, dev2, dev3, int1, int2, int3, plus prod. Customer master file in DB2. Inactive-customer cleanup runs quarterly.

---

## Scene 1 — Thursday, 4:00 PM (60 seconds)

**The setup.** Maya needs to promote `CUST_DELETE_INACTIVE.JCL` from int2 to int3 by end of day. The job deletes customer rows older than 7 years from `MERIDIAN.CUST.MASTER`. Without Helios this would mean: copy the JCL, hand-edit eight region-specific values, trust the wiki page that was last updated when Sarah was on the team (Sarah left two years ago), submit, hope.

**With Helios.**

> Maya opens Helios. She sees the JCL editor open to `CUST_DELETE_INACTIVE.JCL`. Two clicks: source region picker → **int2**. Target region picker → **int3**. She clicks **Promote**.
>
> *Hero frame 1 (cut to Region Atlas diff view, 8 seconds on screen):* Side-by-side YAML diff with seven highlighted substitutions. `DSN SYSTEM(DBI2)` → `DSN SYSTEM(DBI3)`. STEPLIB DSN changed. JES class changed. Plan name changed. RACF user changed. Each highlight has a hover-over reason: "*int3 uses subsystem DBI3*", "*int3 STEPLIB resolves to MERIDIAN.INT3.LOAD*", and so on.
>
> Helios auto-generates a paired backup job below the promotion: `UNLOAD` + `IMAGE COPY` of `MERIDIAN.CUST.MASTER` to `MERIDIAN.INT3.BAK.CUST.MASTER.D2026122.T160000`, retention 30 days. Maya nods, accepts.
>
> *Hero frame 2 (cut to Confidence Score gauge, 6 seconds on screen):* Score animates from 62 (red) → 94 (green). Below the gauge: top reasons. The remaining 6-point gap is one stale copybook reference — `CUSTREC` is pinned to the int2 version. Maya clicks **Apply suggested fix**. Score jumps to 100.
>
> JJSCAN+ panel on the side shows the full dependency graph — every PROC, COPYBOOK, PGM, DD resolved across SYSLIB concatenation order. No red findings.
>
> Maya clicks **Submit for review**. Across the room, Raj's screen pings — a real-time toast from Helios shows the promotion in his Review Queue. Raj clicks the toast → sees the same diff, same score, same reasoning. Approves.
>
> Maya goes home at 5:00.

**Pitch beat:** *"Forty-seven minutes of manual region-hunting and prayer, replaced by six minutes of guided confidence."*

---

## Scene 2 — Three weeks later, 9:00 AM (30 seconds)

**The setup.** A different batch job ran in production overnight. It ABENDed. The on-call developer paged Raj. There's a SYSLOG sitting in everyone's inbox.

**With Helios.**

> Raj opens Helios → **Archaeology**. Pastes the SYSLOG into the dump box. One click: **Diagnose**.
>
> *Hero frame 3 (cut to ABEND Archaeologist three-pane view, 6 seconds on screen):* Left pane — the dump with the abend line highlighted in red: `IGZ0035S CONDITION CODE 7`. Middle pane — Helios identifies it as **S0C7 data exception**, traces the failing instruction to `CUSTPROC.cbl` line 247, paragraph `2300-CALC-RETIREMENT`. Right pane — Granite Code's plain-English explanation:
>
> *"The non-numeric value originated from `CUSTREC.DOB` read at line 142. Field was MOVE'd to `WS-DOB` and used in COMPUTE `WS-CUST-AGE = CURRENT-DATE - WS-DOB` at line 247. The non-numeric value entered the table on 2024-03-12 from BATCH_IMPORT_001 with DOB=NULL. Same root cause as INC-2024-0312 (resolved by adding INITIALIZE statement at line 140)."*
>
> A "Save runbook" button writes the explanation + fix to the team's knowledge base for the next person.

**Pitch beat:** *"Four hours of archaeology by the senior dev, replaced by four minutes any junior can run."*

---

## Closing pitch (10 seconds)

> *"Helios is the AI control plane every mainframe shop wants and nobody's built. Three deep features, one Confidence Score, full audit trail. Built on Bob — every workflow we showed runs through Bob's Skills, MCP servers, and agentic chat. We pre-seeded the demo with MeridianBank, but the architecture works against any region map any shop wants to bring."*

---

## Hero shots — production checklist

These three frames are what the judges screenshot. Each gets twice the design polish of any other UI:

| Frame | Where | Min on-screen time | Owner |
|---|---|---|---|
| Region Atlas diff (7 highlighted substitutions, hover reasons) | Scene 1 | 8 sec | Sayan |
| Confidence Score gauge (62 → 94 → 100 animation, top reasons scrolling) | Scene 1 | 6 sec | Sayan |
| ABEND Archaeologist three-pane view (dump → trace → business explanation) | Scene 2 | 6 sec | Sayan |

## Demo-day production schedule

| Time before judging | Task |
|---|---|
| Day before, 6 PM | Full dress rehearsal with both presenters. Time it. |
| Day of, 9 AM | Backend health check; Cloudant data state correct; demo corpus loaded |
| Day of, 10 AM | Re-record 90-second video as backup (in case live demo glitches) |
| Day of, 11 AM | Browser tabs pre-opened in correct order; clear cache |
| Day of, 30 min before | Restart Bob (fresh Bobcoin counter visible if asked); verify GitHub Pages deploy |
| Day of, 5 min before | Open Helios in primary tab; have backup video tab ready |

## Live demo failure modes — mitigation

| Failure | Fallback |
|---|---|
| Backend down (Code Engine cold start) | Pre-warm at 9 AM; show pre-recorded video if down |
| watsonx.ai latency spike | Cache demo responses in Cloudant; serve from cache if API > 3 sec |
| GitHub Pages deploy stale | Have local `npm run dev` ready as backup |
| WiFi flaky | Mobile hotspot pre-paired; both presenters on same network |
| Live ABEND demo doesn't recognize the dump | Pre-loaded "demo dump" with known-good detection result |

## Speaking roles

**Sayan (frontend, demo flow):** Drives the screen. Talks through Maya's actions. Lands the hero frames.

**Golden (backend, technical depth):** Closes with the pitch. Handles judge Q&A on architecture. Backs Sayan up if anything breaks.

Both wear the same color shirt. Looks intentional, photographs well.

## Q&A preparation

Top 10 anticipated judge questions with prepped answers in `docs/QA_PREP.md` (next file).
