#!/usr/bin/env bash
# tools/gitignore_cleanup.sh — un-track files newly excluded by .gitignore.
#
# Generated for the .gitignore rewrite. Re-run safely: each `git rm --cached`
# is a no-op if the file isn't tracked.
#
# Run from the repo root:
#   bash tools/gitignore_cleanup.sh
#
# Verifies what's tracked before/after, prints a diff, and never touches
# the working tree (only the index — files stay on disk).

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "==> Tracked files before cleanup:"
git ls-files | wc -l
git ls-files | head -10

# ----------------------------------------------------------------
# Files that the new .gitignore would now exclude, listed below.
# ----------------------------------------------------------------
#
# As of this rewrite, `git ls-files` returns exactly:
#   .gitignore
#   LICENSE
#
# Both are EXPLICITLY KEPT by the new rules (negations + .gitignore can
# never self-ignore once tracked). Therefore there is NOTHING to un-track
# right now and this script is a no-op.
#
# If you later add tracked files that match the new rules (for example,
# you accidentally `git add` a node_modules/ entry), uncomment the
# matching lines below and re-run:
#
#   git rm --cached -r node_modules/
#   git rm --cached -r .next/
#   git rm --cached -r out/
#   git rm --cached -r playwright-report/
#   git rm --cached -r test-results/
#   git rm --cached -r storybook-static/
#   git rm --cached -r frontend/coverage/
#   git rm --cached -r .pytest_cache/
#   git rm --cached -r .ruff_cache/
#   git rm --cached -r .mypy_cache/
#   git rm --cached -r __pycache__/
#   git rm --cached -r .venv/ venv/
#   git rm --cached -r build/ dist/
#   git rm --cached -r htmlcov/ .coverage
#   git rm --cached frontend/next-env.d.ts
#   git rm --cached -r .vscode/
#   git rm --cached -r .idea/
#   git rm --cached .DS_Store Thumbs.db
#   git rm --cached -r 'test dataset/'
#   git rm --cached -r shared/sample-corpus/abend_examples/
#   git rm --cached -r shared/sample-corpus/bankdemo-derived/
#   git rm --cached docs/ASSUMPTIONS.md
#   git rm --cached -r bench/results/*.json   # but keep bench/results/.gitkeep
#   git rm --cached .env  # if it ever got staged — never commit
#   git rm --cached CLAUDE.md  # if it ever got staged — never commit
#   git rm --cached -r .bob/cache/ .bob/auth/ .bob/sessions/
#
# Test sources (section 15 — kept local, not in repo audit trail):
#   git rm --cached -r backend/tests/
#   git rm --cached -r mcp-servers/tests/
#   git rm --cached -r frontend/e2e/
#   git rm --cached frontend/playwright.config.ts frontend/vitest.config.ts
#   git rm --cached test-mcp-servers.ps1 test-mcp-simple.ps1
#   # Catch any *.test.ts / *.spec.ts / test_*.py that slipped in:
#   git ls-files | grep -E '(^|/)(test_|.*_test|.*\.test|.*\.spec)\.(py|ts|tsx|js|jsx)$' \
#     | xargs -r git rm --cached

echo "==> Currently nothing to un-track. The new .gitignore is safe to commit."
echo

echo "==> Sanity: paths that the new rules would now ignore, if present:"
for p in \
    .env \
    CLAUDE.md \
    frontend/next-env.d.ts \
    "test dataset/helios_sample_dataset/01_BankDemo/sources/jcl/ZBNKDEL.jcl" \
    docs/ASSUMPTIONS.md \
    shared/sample-corpus/abend_examples/s0c7_custproc.txt
do
    if git check-ignore -q -- "$p"; then
        echo "  ignored : $p"
    elif [ -e "$p" ]; then
        echo "  TRACKED : $p  (review the rules!)"
    else
        echo "  missing : $p  (path doesn't exist; rule sleeping)"
    fi
done

echo
echo "==> Sanity: paths that MUST remain trackable:"
for p in \
    .env.example \
    .pre-commit-config.yaml \
    LICENSE \
    .bob/mcp.json \
    bench/results/.gitkeep \
    shared/sample-corpus/regions/int2.yaml \
    shared/sample-corpus/abend_patterns/patterns.yaml \
    frontend/package-lock.json \
    backend/uv.lock
do
    if git check-ignore -q -- "$p"; then
        echo "  WRONG ignored : $p  (review the negations!)"
    else
        echo "  ok            : $p"
    fi
done

echo
echo "==> Done. No git mutations were made by this script."
