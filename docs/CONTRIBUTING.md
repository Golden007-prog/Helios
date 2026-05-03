# Contributing to Helios

Two-developer hackathon team. Short branches, fast PRs, no Git Flow.

## Branch model

- `main` — always deployable. Protected. Two reviewers required only on `prod` deploys; one reviewer otherwise (the other team member).
- `feat/<owner>/<short-name>` — feature branches, max 4-hour lifetime. Examples: `feat/golden/region-promote-api`, `feat/sayan/confidence-gauge`.
- `fix/<owner>/<short-name>` — bugfix branches, same rules.
- `chore/<owner>/<short-name>` — config, docs, build changes.

Long-lived branches always conflict in two-person work. Cut a new branch for every task; merge within 4 hours; if you can't, the task is too big — break it down.

## Daily flow

```bash
# At session start
git checkout main
git pull origin main
git checkout -b feat/<owner>/<task-name>

# Work, commit often
git add <files>
git commit -m "feat(scope): short imperative description"

# Push and open PR
git push -u origin feat/<owner>/<task-name>
gh pr create --base main --title "<task title>" --body "<what + why>"
```

## Commit message convention

Conventional Commits, lowercase scope, imperative mood:

- `feat(backend): add region promote endpoint`
- `fix(frontend): handle empty copybook list in JJSCAN+ panel`
- `docs(specs): clarify backup retention to 30 days`
- `chore(mcp): wire cloudant server to .bob/mcp.json`
- `test(jjscan): cover GDG version misalignment rule`

**Hard rules.**

- No AI co-author trailers. No "Generated with" footers. No reference to Bob, Claude, Granite, watsonx, or any model in commits or PR descriptions.
- Bob session reports live in `bob_sessions/`. That is the audit trail. Commits read as ordinary human work.
- No commits directly to `main`. Even hotfixes go through a PR (auto-merge if the other person is offline).

## PR template

Copy this into every PR description:

```markdown
## What
<one sentence — what this PR does>

## Why
<one sentence — why it matters; tie to a feature in docs/SPECS.md if applicable>

## How verified
- [ ] Lints pass (ruff for Python, prettier for TS)
- [ ] Tests pass (pytest / vitest)
- [ ] Manually exercised the affected UI / endpoint
- [ ] Bob session report exported to bob_sessions/<owner>/

## Screenshots (if UI)
<paste>

## Notes for reviewer
<anything tricky, anything intentionally out of scope>
```

## Code review

The other team member reviews. Aim for under 30 minutes turnaround during build hours. If the reviewer is offline, use `gh pr merge --auto --squash` and the PR will merge once CI passes.

Review checklist:
1. Does it match the spec in `docs/SPECS.md`?
2. Does it touch the other person's top-level directory? (Reject if yes without coordination.)
3. Are there secrets, AI footers, or `.claude/` artefacts? (Reject.)
4. Is the Bob session report committed?
5. Is there a test for any new logic?

## Squash-merge by default

`Squash and merge` keeps `main` history readable. The squash commit message uses the PR title.

## When to pair instead of split

Pair (call + screen-share) for:
- Schema design that both frontend and backend will consume
- The Region Atlas YAML format
- The Confidence Score weights
- Demo script rehearsal

Split everything else.

## Conflict resolution

If two PRs touch the same file in `shared/`:
1. The PR opened later resolves the conflict.
2. Run the resolved code locally before pushing.
3. Re-request review.

## Bob session reports must travel with the PR

Every PR that produced a visible Helios capability must include the corresponding Bob session export in `bob_sessions/<owner>/` in the same PR. Reviewers reject PRs missing the session report — judging requires the audit trail.

## Pre-flight before any prod-style merge

The `main` branch deploys automatically to GitHub Pages (frontend) and Code Engine (backend) via GitHub Actions. Before merging anything that affects deployment:

- [ ] Backend health endpoint returns 200 locally (`curl localhost:8000/healthz`)
- [ ] Frontend builds without warnings (`npm run build`)
- [ ] No new env vars required without updating `.env.example` and `docs/MCP_SETUP.md`
