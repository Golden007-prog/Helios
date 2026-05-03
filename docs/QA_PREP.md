# Q&A Preparation

The ten questions a judge most likely asks at the end of our 90-second demo. Each has a prepped answer that's truthful, specific, and short enough to deliver in under 30 seconds.

Both presenters should read this and rehearse.

---

## Q1 — "How would this work against a real LPAR?"

> "Helios is designed as a control plane, not an execution engine. It composes JCL, validates it statically, and computes confidence — it never submits to JES. For real LPAR integration, the missing piece is a thin agent on z/OS that streams SMF and SYSLOG events back to our backend, plus FTP/SFTP for promoting the validated JCL into a PDS. That's roughly 2 weeks of work and uses the same architecture; we just didn't have an LPAR to develop against. The MeridianBank synthetic shop in our corpus exercises every code path that would touch a real system."

**Why it works:** acknowledges the gap, scopes the missing work, signals we know what we don't know.

---

## Q2 — "What's actually built versus mocked?"

> "Three features end-to-end on real infrastructure: Region Atlas with promote-job and auto-backup generator, JJSCAN+ with four detection rules running against real COBOL/JCL parsers, ABEND Archaeologist with 15 pre-seeded patterns and Granite Code business explanation. The Confidence Score is real arithmetic over real findings. Everything you saw in the demo runs against the live Code Engine backend and Cloudant database. Only the demo data is synthetic — the platform is not."

**Why it works:** specific scope, no hand-waving.

---

## Q3 — "Why Granite Code instead of <Claude / GPT-4 / Llama 70B>?"

> "Granite Code 8B is genuinely strong on COBOL — IBM trained it on the corpora that power Watson Code Assistant for Z. We benchmarked it against larger models for our specific tasks (copybook drift explanation, ABEND business-rule traceback) and the quality difference doesn't justify the cost or latency. Smaller models also keep us within hackathon credit limits with substantial headroom for live demo traffic. And the larger models on the watsonx menu — Llama 3 405B, Mistral Medium — are on the hackathon's banned list."

**Why it works:** technical, honest, references the hackathon constraint without complaining.

---

## Q4 — "How is this different from Watson Code Assistant for Z?"

> "Watson Code Assistant for Z translates COBOL to Java. Helios doesn't translate anything — it makes the COBOL you're keeping survivable. We're complementary, not competitive. A shop running WCA for Z to modernize 30% of their portfolio still has 70% running unchanged for the next decade, and Helios is what makes that 70% safer to maintain. We could integrate: JJSCAN+ findings could feed WCA's translation prioritization; our Confidence Score could gate WCA-generated PRs."

**Why it works:** positions us alongside an IBM product, not against it.

---

## Q5 — "How does this handle CICS / IMS, not just batch?"

> "Phase 2 roadmap. The Region Atlas schema already models the resource categories CICS and IMS need — transaction codes, RDO definitions, PSB/DBD references. JJSCAN+ rules generalize to CICS resource definitions and IMS PSB scans. We focused on batch JCL for the hackathon because that's where the highest volume of cross-region pain lives, but the architecture isn't batch-specific. Adding a CICS PROC analyzer is roughly the same effort as our COBOL scanner — a couple of weeks."

**Why it works:** shows architectural foresight without overcommitting.

---

## Q6 — "What about security? Who can promote a job?"

> "In the hackathon scope, every authenticated user has full access — we didn't build RBAC. Production design models RACF group membership in the region profile (`racf.groups`), and the Confidence Score formula has a per-region `override_required_role` that gates approvals. Every action writes to an immutable audit log with actor, before/after, and reason. SOX-ready out of the box. The auth integration itself — SSO, RACF passthrough — is a couple of days of work we deferred to keep scope honest."

**Why it works:** concrete on what's there, honest on what's not, names the standard (SOX, RACF) judges expect.

---

## Q7 — "How accurate is the ABEND traceback? How often does it get it wrong?"

> "Pattern matching against the seeded library has a confidence score per match — we surface that. For the COBOL traceback, accuracy depends entirely on parser fidelity; ProLeap COBOL parser handles the constructs in our corpus well, edge cases like complex REDEFINES or copybook macro expansions in older dialects can fail. When the parser confidence is low, the UI says so and falls back to 'this is the abend code, here's the typical cause, here's where to look in the source'. We don't claim 100% — we claim faster and more consistent than human triage."

**Why it works:** quantified honesty beats unhedged confidence with technical judges.

---

## Q8 — "How do you measure success? Are the time savings real?"

> "We measured against the MeridianBank synthetic corpus before submission. JCL promotion: 47 min manual baseline vs 6 min with Helios — timed runs by both team members on a fresh JCL. ABEND root cause identification: 4.3 hr baseline vs 4 min with Helios across the 10 seeded incidents. First-prod-run ABEND rate after promotion: 18% baseline (across 10 manually-edited promotions to int3) vs 0% with Helios. These are corpus numbers, not field numbers — but the corpus mirrors the structure of a real shop closely enough that we're confident the gap holds."

**Why it works:** numbers, methodology, and an explicit caveat. Judges trust honest numbers over inflated ones.

---

## Q9 — "Show me Bob session reports — did you actually use Bob?"

> "Yes — they're in `bob_sessions/golden/` and `bob_sessions/sayan/`. Each report has the full conversation, the consumption summary, and a screenshot. Every visible feature in this demo has a corresponding Bob session: the Region Atlas backend, the JJSCAN+ rules, the Confidence Score gauge, the ABEND three-pane view. Plan-mode chats came first; Code-mode implementation followed. We tracked Bobcoin spend per task in `bob_sessions/<owner>/COIN_LOG.md`. Happy to walk you through any specific one."

**Why it works:** invites verification rather than dodging it. Judges who care about Bob usage are reassured; the rest move on.

---

## Q10 — "What's next if you keep building this?"

> "Three things in priority order. First, the LPAR agent for real SMF/SYSLOG ingestion — turns Helios from a control plane into a closed-loop system. Second, learning-loop maturity — every accept/dismiss feeds Cloudant; once we have data from a real shop, the JJSCAN+ rules tune themselves to the shop's dialect. Third, CI/CD integration — gating PRs on Confidence Score so the promotion check happens at code-review time, not at deploy time. Past that, the natural extensions are RPG and IBM i, since the data model generalizes."

**Why it works:** prioritized, technical, and the priorities make sense.

---

## Bonus — questions you'd rather not get

### "Why didn't you just use Cursor / Copilot / Cline / etc.?"

> "Bob is the IBM hackathon's required tool — that's the constraint we're optimizing for, not a comparison shop. That said, Bob's enterprise focus and full-repository context awareness genuinely matter for a project like Helios where the code knows its own region map. A tool that only sees the file under cursor wouldn't have built this."

### "Have you talked to actual mainframe shops about this?"

> "Not yet — this is hackathon scope. Both of us have studied the public IBM Z DevOps reference architectures, the jjscan documentation, and the Bankdemo corpus that informs our test data. The next step is exactly that — putting Helios in front of a real shop's senior dev for an hour and watching where it breaks for them."

### "What's the business model?"

> "Open source first, Apache 2.0. Commercial extensions for the LPAR agent, RACF integration, multi-tenant hosting. Standard infra-tool playbook — free core, paid enterprise. Not relevant to the hackathon judging but happy to discuss if you're curious."

### "Why is the demo on a synthetic shop instead of real production data?"

> "Production mainframe data is regulated — most shops can't share it for any external project, hackathon or otherwise. The MeridianBank synthetic shop is built from open-source COBOL (GnuCOBOL test suite, Bankdemo, NIST COBOL85) rebadged as a fictional bank. That's the standard pattern for any Z-related demo that isn't on a vendor's own LPAR. The corpus is intentionally large enough to exercise every rule we ship."

---

## Delivery rules

- **Both presenters know all answers.** Don't punt to the other person mid-answer.
- **Under 30 seconds each.** If a judge wants more, they'll ask.
- **Numbers when you have them.** "47 minutes vs 6 minutes" lands harder than "much faster".
- **Never say "we didn't have time".** Say "Phase 2 roadmap" or "out of scope for this submission".
- **Never say "Bob couldn't" or "Granite couldn't".** Say "we observed" or "we found".
- **Always end with a hook.** A noun the judge can ask about — "the LPAR agent", "the learning loop", "the YAML schema". Keeps them engaged.
