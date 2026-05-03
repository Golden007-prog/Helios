# Problem Statement

## The mainframe paradox

Roughly $3 trillion of enterprise transactions flow through z/OS systems daily — banks, insurers, airlines, retailers, governments. The platform is more reliable than anything that came after it. And yet every shop that runs on it is in trouble for the same three reasons:

1. **The talent pool shrinks every year.** Average mainframe developer age is approaching 60. The people who wrote the code are retiring with it.
2. **The code itself is undocumented.** Comments in COBOL programs from 1987 — when they exist — describe what the code did, not why. Business rules live in the heads of people who've already left.
3. **The tooling has not caught up.** ISPF, JCL, JES2, CICS, IMS, DB2 — all rock-solid runtimes wrapped in tooling designed before version control existed.

Modernization-or-die is the wrong frame. Most of these systems will run for another 20 years because rewriting them is too expensive and too risky. The real problem is: *how do you make the next 20 years of maintenance survivable for a workforce that doesn't know COBOL?*

## Three concrete pains we attack

Helios doesn't try to boil the ocean. It picks three specific moments where today's tooling forces every mainframe developer into manual, error-prone, time-wasting work — and where an AI control plane can collapse hours into minutes.

### Pain 1 — Region tribal knowledge

Every mainframe shop runs multiple environments: dev1, dev2, dev3, int1, int2, int3, sometimes more. Each environment has its own:
- Dataset HLQs
- DB2 subsystem ID and collection names
- Plan and package names
- BIND parameters (ISOLATION, ACQUIRE, RELEASE, VALIDATE)
- RACF groups and resource profiles
- JES classes and scheduler queues
- VOLSER conventions
- JOBCARD templates

When a developer promotes a JCL from int1 to int3, every one of these can differ. The "documentation" is a wiki page that was last updated when Sarah was on the team, and Sarah left two years ago. The actual ground truth lives in the heads of three people, two of whom are out today.

The result: developers either copy from a job they ran last week and hope nothing has changed, or they spend 45 minutes tracking down the right values for a 5-minute change. ABENDs in production are routine. Promotions happen Friday afternoon because nobody wants to deal with them earlier in the week.

### Pain 2 — JCL fragility

`jjscan` (jobsCAN) is a venerable IBM Z DevOps utility. It tells you what a JCL calls — which PROCs, which copybooks, which CCLIB members. It does not tell you whether what it calls is **correct**. It does not catch:

- The same copybook name resolving to different physical members across the SYSLIB concatenation
- Two PROCs in the chain that override the same DD with conflicting values
- A program bound to a DB2 plan that doesn't exist in the target region's collection
- A GDG referenced as `(+1)` in a step whose caller already used `(0)`
- A `RESTART=` parameter pointing to a step with `DISP=NEW` on a permanent dataset
- A COND code that makes a step unreachable

These are the failures that cause production ABENDs. The dev who knew about them retired in 2019.

### Pain 3 — ABEND triage as folklore

When a batch job ABENDs at 2am, the on-call developer gets paged. They open the job log, see something like `IEC141I 013-18` followed by 400 lines of JES output, and start the slow archaeology: which step failed, which DD was involved, which dataset, which program, which paragraph in that program, which input record made the program blow up.

For a senior developer who's seen the same ABEND code a hundred times, this takes 20 minutes. For a junior developer who's never seen it, it takes 4 hours and a phone call to the senior developer. The shop's "ABEND oracle" is one or two people who hold all the patterns in their head. When they're on vacation, MTTR triples.

## What changes with Helios

Helios doesn't replace COBOL, JCL, or any of the underlying runtimes. It adds an AI control plane that:

- **Encodes region knowledge as a versioned artifact**, not a wiki page. Every promotion is a diff with reasoning.
- **Catches what `jjscan` won't.** Static analysis informed by the team's own resolution history.
- **Democratizes ABEND triage.** Pattern-library + Granite Code on the source COBOL turns the senior developer's 20-minute mental walk into a 30-second explanation any junior can act on.
- **Attaches a Confidence Score** to every change so reviewers have one number to trust and one place to drill in.

We measure success in time saved on a synthetic but realistic corpus (MeridianBank). Targets in [`docs/JUDGING_ALIGNMENT.md`](JUDGING_ALIGNMENT.md):

| Workflow | Manual baseline | With Helios | Source |
|---|---|---|---|
| JCL promotion int2 → int3 | 47 min average | 6 min | timed runs on MeridianBank |
| ABEND root cause identification | 4.3 hr average | 4 min | ten seeded incidents in the corpus |
| First-prod-run ABEND rate after promotion | 18% | target 0% | ten promotions, scored before vs. after |

Numbers we'll publish in the README the morning of submission.

## Why this is the right scope for a hackathon

Three deep features beats thirteen shallow ones. Every feature in Helios is something a senior mainframe developer can recognize in ten seconds and explain to a non-Z judge in one sentence. That's how we win the Creativity and Effectiveness criteria simultaneously — by being unmistakably useful to the people who live the problem and unmistakably interesting to the people who don't.
