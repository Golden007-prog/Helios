# Team Workspace

Two developers, one repo, parallel work. The single biggest cause of merge hell on a hackathon team is two people editing the same files. This doc is how we avoid that.

## Ownership map

| Directory | Owner | The other person can... |
|---|---|---|
| `frontend/` | **Sayan** | Read; suggest; never edit without coordination |
| `backend/` | **Golden** | Read; suggest; never edit without coordination |
| `mcp-servers/` | **Golden** | Read; never edit |
| `shared/prompts/` | **Either** | Coordinate before commit |
| `shared/schemas/` | **Either** | Coordinate before commit |
| `shared/sample-corpus/` | **Either** | Read-only after initial seed |
| `docs/` | **Either** | Coordinate; PR review catches conflicts |
| `bob_sessions/golden/` | **Golden** | Never touch |
| `bob_sessions/sayan/` | **Sayan** | Never touch |
| `.bob/mcp.json` | **Either** | PR review required |
| `.gitignore`, `CONTRIBUTING.md`, `AGENTS.md`, `README.md` | **Either** | PR review required |

Hard rule: unless explicitly pairing on a single task, do not edit the other person's top-level directory.

## Daily sync ritual (5 minutes, twice a day)

At session start and session end:

```bash
# Both of you
git checkout main && git pull
git log --oneline --author="<other-person>" --since="12 hours ago"
```

A 60-second voice or Slack call:
> *"I'm working on X for the next 3 hours, touching files Y and Z. Anything you're touching that overlaps?"*

If your file lists overlap, swap one task. This single habit prevents 95% of conflicts.

## Parallel work playbook

### When to split

Default. Almost everything. Frontend and backend are naturally separate; shared schemas are the only collision-prone area, and PR review catches them.

### When to pair

Pair (call + screen-share) for:
- The Region Atlas YAML schema design (both frontend Studio UI and backend rewriter consume it)
- The Confidence Score weights (both UI gauge and backend service depend on the contract)
- The first-time setup of any custom MCP server (one person writes, one person verifies it loads on their machine)
- Demo script rehearsal (both of you appear)
- Last-hour submission checks

### When to hand off

Some tasks have a natural baton:
1. Sayan defines the JSON the frontend wants from `/promote`.
2. Golden builds the endpoint to that contract.
3. Sayan integrates and tests end-to-end.

Use a GitHub issue for the handoff so both of you can check it off.

## Bobcoin coordination

Each of you has 40 Bobcoins (per the hackathon allocation visible in the admin portal). Burn rate matters. Coordinate so you're not both running expensive Bob Code-mode tasks simultaneously on overlapping context.

Rough split:
- **Golden — 40 coins.** Backend (~12), MCP servers (~4), Atlas module (~3), Sentry module (~3), buffer + demo prep (~18). Claude Code as silent backup for tasks that would otherwise burn excessive coins.
- **Sayan — 40 coins.** Frontend skeleton + Pages CI (~6), Studio UI (~10), Forge UI (~6), Confidence Score gauge (~6), demo polish (~12).

Full breakdown in [`BOBCOIN_BUDGET.md`](BOBCOIN_BUDGET.md).

## Communication channels

| Need | Tool |
|---|---|
| Quick question | Slack / WhatsApp |
| Pairing on something live | Voice + screen share (Discord / Meet / Zoom) |
| "I'm starting X" / "I finished Y" | Slack channel |
| Detailed design discussion | GitHub issue or PR comment |
| "I committed something risky" | Voice call, immediately |

## Conflict resolution

If two PRs touch the same file in `shared/`:
1. The PR opened later resolves the conflict.
2. Run the resolved code locally before pushing.
3. Re-request review from the other person.

If conflict resolution looks non-trivial, hop on a 5-minute call — faster than ping-ponging in PR comments.

## Bob session sharing

The Memory MCP server (configured in `.bob/mcp.json`) lets Bob remember architecture decisions across sessions. When one of you decides something significant ("we're going with `proleap-cobol-parser` for AST"), tell Bob to remember it:

> *Remember that we use proleap-cobol-parser for COBOL AST in this project.*

Bob writes it to the memory graph. Next session, on either machine, Bob recalls it. Free architectural alignment.

## What both of you must do every session

Before logging off:

- [ ] All work committed and pushed (no work-in-progress on local-only branches)
- [ ] Bob session reports for completed tasks exported to `bob_sessions/<your-name>/`
- [ ] Reports committed and pushed
- [ ] Outstanding PRs marked as ready for review or as draft
- [ ] Slack message: "Done for now. Picking up X next session. Y is queued for you to review."

## When the other person is offline

You're not blocked.

- Your PR reviewer is offline → use `gh pr merge --auto --squash`. Merges when CI passes.
- You need a frontend change but only backend exists → mock the backend response in frontend code, leave a `TODO(integrate)` comment with a GitHub issue link.
- You're worried you'll forget context → write it in the GitHub issue, not just in your head.

## Conflict-prone moments — extra care

- **First commit on `main`** — only Golden does this (repo owner), with `.gitignore`, `.gitattributes`, folder skeleton.
- **Schema changes in `shared/schemas/`** — always pair on these.
- **`.bob/mcp.json` edits** — both of you should restart Bob after pulling to confirm the new config loads.
- **Demo script changes in `docs/DEMO_SCRIPT.md`** — pair on these. Demo is the highest-stakes artifact.

## Emergency rollback

If `main` is broken and you can't fix-forward in under 10 minutes:

```bash
git revert <sha-of-bad-commit>
git push origin main
```

Then call the other person.
