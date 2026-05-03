# Runbook — local dev, deploy, rollback, common errors

For when something needs running, redeploying, or unbreaking. For *what*
the system does, see `docs/ARCHITECTURE.md`. For *why* and *when*, see
`docs/PHASE_PLAN.md`.

---

## 1. Local dev

### One-shot setup

```bash
# 1. Repo + env
git clone <fork> Helios && cd Helios
cp .env.example .env                  # fill in secrets, see docs/KICKOFF_CHECKLIST.md
cp frontend/.env.example frontend/.env.local

# 2. Install
make install                          # backend + mcp-servers + frontend deps
cd frontend && npx msw init public/ --save && cd ..

# 3. Cloudant + seed (optional — backend boots in-memory without it)
make seed

# 4. Run
make dev                              # backend on :8080, frontend on :3000
```

### Without Cloudant or watsonx credentials

The backend boots in **degraded mode** when credentials are missing:

* `CloudantClient` falls back to an in-memory dict (no persistence).
* `WatsonxClient` returns labeled stub responses.
* `/readyz` returns 503 with the failed-dependency name.

This is intentional — every developer can run `make dev` without IBM Cloud
provisioned. Only the demo and CI deploy paths require live deps.

## 2. Deploy

### Backend → Code Engine

Auto: pushing to `main` runs `.github/workflows/backend-deploy.yml`. The
build job pushes the image; the deploy job is gated on a `production`
GitHub environment manual approval.

Manual:

```bash
IMAGE_TAG=$(git rev-parse --short HEAD) bash backend/deploy/deploy.sh
```

Required env: `IBM_CLOUD_API_KEY`, `IBM_CLOUD_REGION`, the `helios-env`
secret in the `helios-prod` Code Engine project.

### Frontend → GitHub Pages

Auto: `.github/workflows/frontend-deploy.yml` runs on changes under
`frontend/` or `shared/`. Uses `actions/deploy-pages@v4`.

Manual:

```bash
make deploy.frontend                  # → frontend/out/
```

Then upload `frontend/out/` via the Pages UI or push to a `gh-pages`
branch.

## 3. Rollback

### Backend

```bash
ibmcloud ce app update --name helios-backend --image icr.io/helios/helios-backend:<previous-sha>
```

Code Engine does a fresh deploy with the old image. `/version` will
reflect the rolled-back SHA.

### Frontend

GitHub Pages serves the most recent successful build. To roll back:

1. `git revert <bad-sha>` on `main`.
2. Push — the workflow re-deploys the reverted state.

If the bad commit is unrecoverable (e.g. secret leaked into a build), use
the GitHub UI: Actions → frontend-deploy → previous successful run →
"Re-run all jobs". This re-publishes the prior artifact without needing a
new commit.

## 4. Common errors

### `app.jobs.runner` import fails

Most likely a stale tree from before the bootstrap. Re-pull `main`. The
in-memory runner lives at `backend/app/jobs/runner.py`.

### `make typegen` fails with `ModuleNotFoundError: No module named 'app'`

Run from the repo root, not from `backend/`. The codegen scripts add
`<repo>/backend` to `sys.path` automatically — they need the repo root as
CWD to do so.

### Frontend: "Booting mock backend…" never resolves

`public/mockServiceWorker.js` is missing or corrupted. Run:

```bash
cd frontend && npx msw init public/ --save
```

The committed file is a placeholder; the real worker is generated.

### Bob can't see custom MCP servers

`.bob/mcp.json` has `disabled: true` on every custom server by default.
Flip to `false` only after that server's phase is reached and its env
vars are set in the shell that launched Bob. See
`docs/MCP_SETUP.md § Troubleshooting`.

### Cloudant 401 on every call

Service key was probably created with `Reader` instead of `Manager`.
Recreate:

```bash
ibmcloud resource service-key-delete helios-cloudant-key
ibmcloud resource service-key-create helios-cloudant-key Manager --instance-name helios-cloudant
```

### `BobStubError` returns 501 in tests — is that a failure?

No — that's the contract test working correctly. When Bob lands the hero
feature, the contract test for that endpoint must be updated in the same
PR; until then, 501 + `BOB:` is the desired state.

### CI fails: "generated files are stale — run `make typegen`"

The Pydantic models changed without regenerating the TS counterparts. Run
`make typegen` and commit the diff under `shared/schemas/` and
`frontend/src/lib/api/*.gen.ts`.

## 5. Day-of-demo checklist

See `docs/TESTING.md § 7` for the printable pre-demo checklist. Tape it
next to the laptop. The most-bitten-by item: launching Bob from Spotlight
on macOS — env vars don't inherit; MCP dots go red mid-demo. Always
launch Bob from the terminal that has `.env` sourced.
