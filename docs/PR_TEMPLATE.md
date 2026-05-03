# Pull Request

## What
<!-- One sentence — what this PR does. -->

## Why
<!-- One sentence — why it matters. Link to a feature in docs/SPECS.md if applicable. -->

## How verified
- [ ] Lints pass (`ruff check` for Python, `prettier --check` for TS)
- [ ] Tests pass (`pytest` / `vitest`)
- [ ] Manually exercised the affected UI / endpoint
- [ ] Bob session report exported to `bob_sessions/<owner>/`
- [ ] No secrets in diff (`git diff --staged | grep -iE "(api_key|apikey|ghp_|password|secret)"` returns nothing)
- [ ] No AI co-author trailers, no "Generated with" footers

## Screenshots (if UI changes)
<!-- Paste before/after if applicable. Mask any credentials. -->

## Coins burned
<!-- ~N (Plan mode X, Code mode Y, MCP calls Z). See docs/BOBCOIN_BUDGET.md. -->

## Notes for reviewer
<!-- Anything tricky. Anything intentionally out of scope. Anything you want extra eyes on. -->

## Linked issue
<!-- Closes #N — or "n/a" -->

---

<!--
Reminder for reviewer:
1. Does it match the spec in docs/SPECS.md?
2. Does it touch the other person's top-level directory? (Reject if yes without coordination.)
3. Are there secrets, AI footers, or .claude/ artefacts? (Reject.)
4. Is the Bob session report committed?
5. Is there a test for any new logic?
-->
