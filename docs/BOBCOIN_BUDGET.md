# Bobcoin Budget

How to spend the team's 80 Bobcoins (40 per developer) so the demo ships and you don't ration yourself into a corner on day three.

The principle: **Bobcoins are a budget, not a leaderboard.** Burning fewer doesn't win you anything. Running out before demo day loses you everything. Spend deliberately.

This doc pairs with `docs/WORKFLOW.md` (mode patterns) and `docs/PHASE_PLAN.md` (what gets built when).

---

## Total budget

| Pool | Coins | Notes |
|---|---|---|
| Golden's Bob coins | 40 | Backend, MCP, infra |
| Sayan's Bob coins | 40 | Frontend, polish |
| Golden's Claude Code | unbounded* | Sidecar, ~$5 in Anthropic Pro time |
| Sayan's Claude Code | none | Single-IDE on frontend by design |

*Claude Code is rate-limited but not coin-priced; in practice Golden has effectively unlimited fallback for backend work, which is why his coin pool is identical to Sayan's despite owning more code.

## Per-sub-phase allocation

The numbers below are upper bounds. Hit them and you should *stop* and re-plan, not push through.

### Phase 1.1 — Foundations

| Owner | Task | Coin ceiling |
|---|---|---|
| Golden | Repo + FastAPI scaffold | 1 |
| Golden | Cloudant client + indexes | 2 |
| Golden | **audit_writer with hash chain** | 4 |
| Golden | RFC 8785 canonicalization + test vectors | 2 |
| Golden | `helios-corpus` MCP server | 2 |
| Golden | `cloudant` MCP server | 2 |
| Sayan | Next.js scaffold + Tailwind tokens | 2 |
| Sayan | Layout shell + nav | 2 |
| Sayan | Auth bootstrap (login page) | 2 |
| Sayan | WebSocket hook scaffold | 1 |

**Phase total: ~20 coins (Golden 13, Sayan 7).** This is high relative to demo visibility because foundations matter.

### Phase 1.2 — Region Atlas

| Owner | Task | Coin ceiling |
|---|---|---|
| Golden | Region schema + 7 seed YAMLs | 2 |
| Golden | Diff engine | 2 |
| Golden | Substitution engine | 2 |
| Golden | Region API endpoints | 1 |
| Sayan | Atlas tab + region cards | 2 |
| Sayan | Region detail YAML view | 2 |
| Sayan | **Diff view (Monaco diff editor)** | 3 |
| Sayan | Promote wizard skeleton | 2 |

**Phase total: ~16 coins (Golden 7, Sayan 9).**

### Phase 1.3 — JJSCAN+ + Confidence Score

| Owner | Task | Coin ceiling |
|---|---|---|
| Golden | Rule framework | 2 |
| Golden | 4 rules with golden tests | 4 |
| Golden | `POST /api/scan` + decide endpoints | 1 |
| Golden | Backup generator | 2 |
| Golden | **Score engine (formula + breakdown)** | 3 |
| Golden | `POST /api/promote` | 2 |
| Golden | Learning Loop dissent query | 1 |
| Sayan | Studio tab + JCL viewer | 2 |
| Sayan | **Confidence Score gauge (Recharts)** | 2 |
| Sayan | Score breakdown panel | 2 |
| Sayan | Findings list + auto-fix UI | 2 |
| Sayan | Dissent banner | 2 |

**Phase total: ~25 coins (Golden 15, Sayan 10).** This is the demo's centerpiece — invest here.

### Phase 1.4 — ABEND Archaeologist

| Owner | Task | Coin ceiling |
|---|---|---|
| Golden | ABEND family taxonomy | 1 |
| Golden | **Classifier with confidence tiers** | 3 |
| Golden | Pattern library (~15 entries) | 3 |
| Golden | `POST /api/abend` with degradation logic | 2 |
| Golden | `watsonx` MCP server | 2 |
| Golden | Granite prompt template + grounding | 2 |
| Golden | Runbook generator + lookup | 2 |
| Sayan | Three-pane ABEND tab | 3 |
| Sayan | SYSLOG parser feedback | 1 |
| Sayan | Source view jump-to-line | 1 |
| Sayan | Analysis pane + ranked causes | 2 |
| Sayan | Unfamiliar-tier banner | 1 |

**Phase total: ~23 coins (Golden 15, Sayan 8).**

### Phase 1.5 — Review Queue

| Owner | Task | Coin ceiling |
|---|---|---|
| Golden | Cloudant `_changes` listener | 2 |
| Golden | **WebSocket endpoint with RBAC** | 3 |
| Golden | Auto-approve policy engine | 1 |
| Golden | Approve/reject endpoints | 1 |
| Sayan | Review tab + queue cards | 2 |
| Sayan | **Mobile-responsive layout** | 2 |
| Sayan | Reconnect-with-backoff logic | 1 |
| Sayan | Toast notifications (both sides) | 1 |

**Phase total: ~13 coins (Golden 7, Sayan 6).**

### Phase 1.6 — Polish + rehearsals

| Owner | Task | Coin ceiling |
|---|---|---|
| Golden | Resilience scenarios green | 2 |
| Golden | Performance budget tuning | 2 |
| Sayan | Hero shots pixel-exact | 3 |
| Sayan | Demo dry-run polish | 2 |
| Both | Doc updates from build learnings | 2 |

**Phase total: ~11 coins (Golden 4, Sayan 5, shared 2).**

### Sum

| Owner | Sum across phases | Allocated | Buffer |
|---|---|---|---|
| Golden | 61 | 40 | -21 → covered by Claude Code |
| Sayan | 45 | 40 | -5 → tight, must be disciplined |

The math works because Golden has Claude Code. Sayan has 5 coins of slack — that's why frontend work uses mocked data, reuses Tailwind tokens, and avoids component libraries beyond what's in `docs/TOOLS_AND_SERVICES.md`.

## Coin-spending modes

### Plan mode is cheap

Plan mode reads files and proposes changes without writing. Bob's plan-mode roundtrips are ~0.1-0.3 coins each. Use it freely for design discussions.

### Act mode costs more, scales with output

Act mode generates code. A 100-line React component costs ~0.5-1.0 coin; a 500-line backend service costs ~1-2 coins. Big single-shot generations are coin-efficient compared to many small iterations.

### Iterating on the same file is expensive

Re-reading a file repeatedly costs each time. Strategies that save coins:

- **Hand-edit small tweaks.** Renaming a variable doesn't need Bob.
- **Batch related changes into one Bob task.** "Update the score gauge color and add the breakdown tooltip" is one task, two coins. Doing them as separate tasks costs three.
- **Use the filesystem MCP for re-reads.** Bob's filesystem MCP read is much cheaper than asking Bob to read a file.

### Memory MCP is free leverage

Once Bob has a project convention in memory ("we use Pydantic v2 not v1," "all errors return the standard envelope," "audit_writer must be called for state changes"), it stops asking. Memory is preloaded by reading `AGENTS.md`; you don't pay for that on every task.

## When to fall back to Claude Code (Golden only)

Three triggers:

1. **You're at the coin ceiling for a task and the task isn't done.** Don't push through with Bob; switch to Claude Code, finish, come back.
2. **You're doing a >5-file refactor.** Linear coin cost in Bob, single-shot in Claude Code.
3. **Bob has tried the same thing 3 times and is going in circles.** Different model, different angle, often unblocks.

Rules when using Claude Code:

- Read `docs/templates/CLAUDE.md.template` once at session start
- No co-author trailers in commits
- No Claude/Anthropic references in code or comments
- Output is reviewed by Golden, then committed by Golden
- Bob's session export still happens at end of day — note in the day's summary "used Claude Code for X"

Sayan does not use Claude Code. The team needs one source of truth on the frontend; dual-IDE on the same code path causes merge churn that costs more than it saves.

## Tracking — keep it simple

The PR template asks "Coins burned" with a single number. Estimate from Bob's session view at the time you open the PR — don't try for precision. The point is to spot trends ("Sayan's been burning 8 coins per UI feature when budget says 3 — investigate").

End-of-week tally:

```bash
grep -h "Coins burned" $(find . -name "*.md" -newer reference-date) | sort
```

If either dev is >20% over budget for the week, **re-plan with the partner**. The fix is usually scope reduction, not "try harder."

## Anti-patterns

Things that burn coins fast for little return:

| Anti-pattern | What to do instead |
|---|---|
| Asking Bob to read the whole codebase to "get context" | Point Bob at the specific files via filesystem MCP |
| Asking Bob to "improve this" without specifics | Specify the desired behavior change, with a test |
| Iterating on copy/microcopy with Bob | Hand-write copy; it's faster |
| Asking Bob to write tests after the fact | Write tests with the implementation in the same task |
| Using act mode for design exploration | Plan mode for design, act mode for execution |
| Re-running a failing task without diagnosing | Read the error, fix the precondition, then re-run |
| Asking Bob to "make it look nicer" | Specify the design change (color, spacing, layout) |

## Anti-anti-pattern

A few things look like they should burn coins but don't:

- **Reading lots of docs at session start.** Bob caches reads within a task; reading 5 docs upfront is cheaper than discovering you needed them later.
- **Writing detailed PR descriptions.** Future Bob sessions read your PRs to understand context; well-written PRs are an investment.
- **Adding comments to non-obvious code.** Bob reads comments next time; the comment pays for itself in coin savings on day 3.

## What about post-hackathon?

Phase 2 doesn't have Bobcoins; Phase 2 has actual money. The discipline transfers:

- Plan before acting
- Small PRs reviewed quickly
- Spec the contract, build to spec
- One IDE per area of the codebase

The habits matter more than the meter.

## What this doc is NOT

- Not the workflow — that's `docs/WORKFLOW.md`
- Not the phase plan — that's `docs/PHASE_PLAN.md`
- Not the tool inventory — that's `docs/TOOLS_AND_SERVICES.md`

## One sentence

> 80 coins, ~75 coins of build at ceiling, ~25% buffer if both devs follow plan-mode-first discipline; Golden's overage gets covered by Claude Code, Sayan's discipline shows up in clean Tailwind-only UI work and mocked data during build.
