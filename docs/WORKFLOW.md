# Workflow — Daily Ritual

The daily flow that makes Bob + a two-person team productive. The structure is "morning sync → focused work blocks → end-of-day export." Follow the structure even on day three when you're tired — that's exactly when the structure pays off.

This is the operational doc. For coin discipline see `docs/BOBCOIN_BUDGET.md`. For the build sequence see `docs/PHASE_PLAN.md`. For Bob configuration see `docs/MCP_SETUP.md`.

---

## The shape of a day

| Block | Duration | Purpose |
|---|---|---|
| 1. Morning sync | 15 min | Align on day's goals, surface blockers |
| 2. Focused work block | 90-120 min | Heads-down build |
| 3. Mid-block check | 5 min | "Am I on track? Should I keep going or pivot?" |
| 4. Lunch / break | 30-60 min | Real break, away from screen |
| 5. Focused work block | 90-120 min | Heads-down build |
| 6. Mid-afternoon sync | 15 min | Re-align, share what's landing |
| 7. Focused work block | 60-90 min | Wrap-up, integration |
| 8. End-of-day export | 20 min | PR, push, session export, close laptop |

Total: ~7 productive hours. Anything more and quality drops; you'll re-do work tomorrow.

---

## 1. Morning sync (15 min)

In person if you're co-located, video call otherwise. Same time every day — pick 9:30 or 10:00, stick to it.

Three questions, in order:

1. **What did you ship yesterday?** (Not "what did you work on" — what *merged*.)
2. **What are you shipping today?** Pick the next sub-phase ticket from `docs/PHASE_PLAN.md`.
3. **What's blocking you?** Anything where you're stuck, the other dev might know, or that crosses the API contract.

Write the day's plan in a 3-line note. Pin it in your shared Slack/Discord. End of day: confirm what landed.

**Rules.** No design discussions in sync. If you discover a design question, **schedule a 15-min sidebar after sync** — don't let it eat the standup. The point of sync is to align, not solve.

## 2. Focused work block (90-120 min)

The Bob-driven half of your day. Phone on Do Not Disturb. Slack/Discord notifications muted. Single browser window. One feature in flight at a time.

### Pre-Bob (5 min)

Before opening Bob:

- Read the spec doc for what you're building (e.g., `docs/REVIEW_QUEUE.md` for the WebSocket flow).
- Open `AGENTS.md` in a side panel — Bob will read it, you should too.
- Identify the API contract: which endpoint's behavior are you changing, and does `docs/API.md` already specify it? If yes, build to spec. If no, **spec it first** by editing `docs/API.md` in the same PR.
- Pick a branch name: `feat/<sub-phase>-<thing>` (e.g., `feat/1.3-confidence-score`).

```bash
git checkout main && git pull
git checkout -b feat/1.3-confidence-score
```

### During Bob

The mode discipline that saves coins:

- **Plan mode for design.** Bob proposes the file changes, you approve. Don't act-mode through architectural choices.
- **Act mode for typing.** Once the plan is locked, switch to act mode for the actual edits.
- **Auto-approve writes only after plan confirms.** If Bob's plan involves files you didn't expect, that's a sign the plan is wrong — push back.

When Bob asks a clarifying question, **the answer often lives in `docs/`**. Search there first; if not there, the question is real and needs a human answer.

When Bob is about to fall down a rabbit hole (3+ minutes of "trying" something), stop. Re-plan. The wall is usually a missing precondition (env var, dependency, doc) not a hard problem.

### Mid-block check (5 min)

Set a timer for 90 minutes when you start. When it goes off:

- Have I shipped something I could push? If yes, push (don't merge yet — just push the branch).
- Am I ahead, on track, or behind on today's ticket?
- If behind: scope down or ask for help.
- If ahead: what's the next ticket I'd take?

The check is the discipline that keeps you from accidentally spending six hours on a thing you should have descoped at hour two.

## 3. End-of-day export (20 min)

The 20 minutes that distinguish a chaotic team from a smooth one. Do all of this even when you're tired.

### A. Wrap the working branch

```bash
# If your branch is ready for review
git push origin feat/1.3-confidence-score
gh pr create --fill   # uses docs/templates/PR_TEMPLATE.md
```

The PR template asks for:

- What's in this change
- How to test it (curl commands or UI clicks)
- Coins burned (rough estimate from Bob's session view)
- Linked spec doc
- Linked sub-phase from `docs/PHASE_PLAN.md`

Fill all four. Future-you will thank present-you.

### B. Export the Bob session

Bob → File → Export Session → save to:

```
bob_sessions/<your-name>/YYYY-MM-DD-<feature>.json
```

Then commit:

```bash
git add bob_sessions/
git commit -m "session: 1.3-confidence-score"
git push
```

This is a judging deliverable per `docs/DOCS_INDEX.md`. Skipping it forfeits points. It also provides forensic value when something breaks at 11 p.m. — you can replay what Bob did.

### C. End-of-day sync (5 min, async)

Post in your shared channel:

> Today: shipped X (PR #N), opened Y (PR #M, blocked on Z).
> Tomorrow: starting on W (sub-phase 1.4 ticket A).
> Coins burned: ~12.

Read your partner's post. If their blocker is something you can unblock in 5 minutes, do it before closing the laptop.

### D. Close cleanly

- All work either pushed or stashed (no dangling local changes)
- `.env` not in `git status`
- Bob session exported
- Laptop sleep, not just screen lock
- Phone off DND if you want it back

## Branch naming

`<type>/<sub-phase>-<thing>`

| Type | When |
|---|---|
| `feat/` | New feature or capability |
| `fix/` | Bug fix |
| `docs/` | Doc-only change |
| `chore/` | Tooling, deps, refactors with no behavior change |
| `wip/` | Personal scratch branch, never merged to main |

Examples: `feat/1.2-region-diff`, `fix/audit-chain-ordering`, `docs/abend-unknown-handling`, `chore/bump-fastapi-115`.

## Commit messages

Conventional commits. One line, present tense, imperative.

```
feat(score): add backup_gap penalty
fix(audit): correct prev_event_hash on first event
docs(api): document state_transition_invalid error code
chore(ci): bump pytest to 8.x
```

If the commit needs more than one line, that's a sign it should be two commits.

**Never** include AI co-author trailers. The work is the team's. (Also, never include them. See `AGENTS.md` Hard rules.)

## Pull requests

Use the PR template. Keep PRs small — under 400 lines diff is the target. Larger PRs cost both reviewers more attention than they save in convenience.

The two-person review:

1. Author opens PR with description filled in
2. CI runs (`ci.yml`) — must be green before review
3. Other dev reviews in <90 minutes
4. Author addresses comments, force-push allowed pre-review
5. Author squash-merges (preserves PR-level history, drops noisy commits)
6. Author deletes branch immediately

Reviewer's job is **not** to redesign — it's to catch:

- API contract drift (does this match `docs/API.md`?)
- Missing audit_writer call on a state-changing endpoint
- Tests for the new code path
- Co-author trailers (block)
- Secrets in code (block)

If the PR needs design changes, comment "let's pair on this" and book 15 minutes — don't ping-pong async on architecture.

## Mode patterns — when to use what

### Bob plan mode

- Design discussions
- Multi-file refactors
- Anything you want a "what's about to happen" summary on
- Cross-cutting concerns (e.g., "add audit_writer call to all state-changing endpoints")

### Bob act mode

- Implementing a clear spec
- Following a plan from a previous plan-mode session
- Mechanical work (fixing lint, updating types, renaming)

### Claude Code (Golden only)

When Bob runs out of coins mid-task, or when a backend task involves >5 files of refactor that would burn coins linearly. Rules per `AGENTS.md`:

- Output is reviewed and re-committed by Golden
- No co-author trailers
- No Claude/Anthropic references in code

### Manual coding (no AI)

- Tweaks under 5 lines
- Renaming a variable
- Editing a config value
- Anything where opening Bob would take longer than the actual change

## Sayan's coin reality

Sayan's pool is smaller (no Claude Code sidecar). Optimization rules:

- **Storybook scaffolding once, reuse forever.** Don't burn coins regenerating the same component shell.
- **Tailwind, not bespoke CSS.** Tailwind is faster to instruct Bob on; bespoke CSS doubles iteration cost.
- **Mock data, not live calls during build.** Hit the live backend only for integration testing, not while iterating on UI.
- **Component libraries reused.** Monaco, Recharts, lucide are already in `package.json` per `docs/TOOLS_AND_SERVICES.md`. Don't pick a fifth.

Daily coin target for Sayan: **<10/day**. If you're burning more, something is off.

## Conflict resolution

When the two devs disagree:

1. **API contract or data model conflict?** The doc wins. If the doc is wrong, edit the doc *first* in a separate PR, then resolve.
2. **Design preference?** The owning dev decides — Sayan owns frontend choices, Golden owns backend choices.
3. **Cross-cutting concern (audit log, error envelope, naming)?** 15-min sidebar, write the decision into the relevant doc, move on.

Don't let a disagreement linger past one day. Decisions cost less than indecision.

## What this workflow is NOT

- Not the kickoff — that's `docs/KICKOFF_CHECKLIST.md`
- Not the build sequence — that's `docs/PHASE_PLAN.md`
- Not the coin allocation — that's `docs/BOBCOIN_BUDGET.md`
- Not the test regime — that's `docs/TESTING.md`

## One sentence

> Sync at 9:30, two heads-down blocks per half-day with a discipline check at 90 minutes, ship in small PRs reviewed in under 90 minutes, export your Bob session every evening, sleep on time. The cadence is the productivity.
