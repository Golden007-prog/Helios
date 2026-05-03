# Deployment

How Helios goes from your laptop to a publicly reachable URL. Two GitHub Actions workflows handle it: `deploy-backend.yml` (FastAPI → IBM Code Engine) and `deploy-frontend.yml` (Next.js → GitHub Pages). Both are already in `.github/workflows/`. This doc is the prose explainer + the GitHub secrets you need to set + how to roll back when it goes wrong.

For local install see `docs/INSTALLATION.md`. For the build sequence see `docs/PHASE_PLAN.md`.

---

## Architecture

```
┌─────────────────────┐         HTTPS            ┌─────────────────────────┐
│ helios.github.io    │ ───────────────────────► │ IBM Code Engine         │
│ (Next.js static)    │ ◄─── WebSocket ──────────│ (FastAPI + uvicorn)     │
│ on GitHub Pages     │                          │ scale-to-zero, 0-5 inst │
└─────────────────────┘                          └─────────────────────────┘
                                                          │
                                                          ▼
                                          ┌──────────────────────────────┐
                                          │ Cloudant Lite + watsonx.ai   │
                                          │ (us-south)                   │
                                          └──────────────────────────────┘
```

Why split:

- **Static frontend on Pages** — free, fast CDN, no backend dependency for the marketing/landing surface
- **Backend on Code Engine** — needed for WebSocket + watsonx + Cloudant; scale-to-zero means $0 when idle
- **Cloudant + watsonx in same region** as Code Engine (`us-south`) to avoid egress charges

If the backend goes down on demo day, the frontend still loads and shows a friendly degraded banner. If GitHub Pages is down, the backend is unaffected. Decoupling is demo insurance.

## Required GitHub secrets

Set these in the repo at Settings → Secrets and variables → Actions → Repository secrets.

### For backend deploy

| Secret | Where to get it | Scope |
|---|---|---|
| `IBM_CLOUD_API_KEY` | `cloud.ibm.com → Manage → Access (IAM) → API keys` | Editor on Code Engine, Reader on Container Registry |
| `IBM_CLOUD_REGION` | Static value | `us-south` |
| `CODE_ENGINE_PROJECT` | Static value | `helios-prod` |
| `CODE_ENGINE_APP_NAME` | Static value | `helios-backend` |
| `IBM_CLOUD_REGISTRY` | Static value | `us.icr.io/helios` |

### For frontend deploy

| Secret | Where to get it | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | After backend deploys, copy the public URL | e.g., `https://helios-backend.<hash>.us-south.codeengine.appdomain.cloud` |
| `NEXT_PUBLIC_WS_URL` | Same host, `wss://` scheme, `/ws/queue` path | e.g., `wss://helios-backend.<hash>.us-south.codeengine.appdomain.cloud/ws/queue` |

These are `NEXT_PUBLIC_*` because they're baked into the static build and visible to anyone inspecting the page. **Never** put backend API keys in frontend env vars.

### For backend runtime (set on the Code Engine app, NOT in GitHub)

The deploy workflow doesn't propagate these — set them once on the app via `ibmcloud ce` or the Code Engine UI:

```bash
ibmcloud ce app update --name helios-backend \
  --env CLOUDANT_URL=https://... \
  --env CLOUDANT_APIKEY=... \
  --env WATSONX_URL=https://us-south.ml.cloud.ibm.com \
  --env WATSONX_PROJECT_ID=... \
  --env WATSONX_APIKEY=... \
  --env JWT_SECRET=... \
  --env CORS_ORIGINS=https://Golden007-prog.github.io
```

After updating env, Code Engine restarts the app automatically.

**Why this split.** GitHub-stored secrets are visible to anyone with repo write access; runtime secrets on Code Engine are visible only to IBM Cloud account members. Putting `CLOUDANT_APIKEY` in GitHub would mean every contributor sees the production database key.

## How `deploy-backend.yml` works

Triggered on push to `main` if `backend/**` or `shared/**` changed. Steps:

1. **Test gate** — runs `pytest -q` against the backend. If tests fail, deploy is skipped.
2. **IBM Cloud login** — uses `IBM_CLOUD_API_KEY` to authenticate `ibmcloud` and `ibmcloud cr`.
3. **Build + push image** — `docker build -t us.icr.io/helios/helios-backend:<sha> -f backend/Dockerfile backend` then `docker push`.
4. **Update or create Code Engine app** — if the app exists, `ibmcloud ce app update --image <new>`. If not, `ibmcloud ce app create` with port 8080, scale 0-5, 1 GB / 1 vCPU.
5. **Smoke check** — polls `${URL}/healthz` for up to 30 s. If it doesn't return `{"ok":true}`, the workflow fails (loudly).

Total runtime: 4-7 minutes, mostly the docker build.

The full workflow YAML is at `.github/workflows/deploy-backend.yml` — it's deliberately simple, no clever tricks. If a step needs explaining, it gets a comment in the YAML, not a note here.

## How `deploy-frontend.yml` works

Triggered on push to `main` if `frontend/**` changed. Steps:

1. **Build** — `npm ci` + `npm run build` with `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_WS_URL` injected.
2. **Configure Pages** — `actions/configure-pages@v4` sets up the right output paths.
3. **Upload artifact** — pushes `frontend/out/` to GitHub.
4. **Deploy** — GitHub publishes the artifact to `https://Golden007-prog.github.io/Helios/`.

Total runtime: 2-3 minutes.

Concurrency is set to `pages` with `cancel-in-progress: false` — if you push twice in 30 seconds, both deploys queue and run in order. This prevents the "second push wins, first push's CDN-purge race condition" class of bug.

## First deploy — order of operations

The two workflows have an ordering dependency only the first time, because the frontend needs the backend's URL.

1. **Push the backend first.** Empty stub is fine — just a `/healthz` that returns `{"ok":true}`.
2. **Wait for the backend deploy to finish.** Note the URL (`ibmcloud ce app get --name helios-backend --output url`).
3. **Set `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_WS_URL`** in GitHub secrets.
4. **Push the frontend** (or trigger `deploy-frontend.yml` manually with `workflow_dispatch`).

After this, both workflows are independent — push one without the other freely.

## CORS

Backend's `CORS_ORIGINS` env var must include the frontend's exact origin. For our setup:

```
CORS_ORIGINS=https://Golden007-prog.github.io,http://localhost:3000
```

Localhost is included so dev hits the deployed backend without a separate config.

If you see CORS errors after a frontend deploy, the most common cause is the trailing slash mismatch — `https://Golden007-prog.github.io/` (with slash) vs `https://Golden007-prog.github.io` (without). Use **without**. Browser strips trailing slashes from origins.

## Smoke test the deploy

After every deploy, manually verify:

```bash
URL=$(ibmcloud ce app get --name helios-backend --output url)

# Backend up?
curl -fsS "$URL/healthz" | jq

# Backend ready (Cloudant + watsonx reachable)?
curl -fsS "$URL/readyz" | jq

# Login flow works?
TOKEN=$(curl -fsS -X POST "$URL/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"maya@meridianbank.demo","password":"helios2026"}' \
  | jq -r .data.token)
echo "Token: $TOKEN"

# Frontend loads?
curl -fsI https://Golden007-prog.github.io/Helios/ | head -1
```

All four should succeed. If any fails, see § Troubleshooting below.

## Rollback

### Backend rollback

Code Engine keeps the previous N revisions. Roll back to a previous revision:

```bash
ibmcloud ce app revision list --app helios-backend
# pick the revision before the broken one
ibmcloud ce app update --name helios-backend --revision <revision-name>
```

Or roll back to a previous image SHA:

```bash
ibmcloud ce app update --name helios-backend --image us.icr.io/helios/helios-backend:<previous-sha>
```

The image SHA is the first 7 chars of the git commit it was built from — you can find it in the Actions log of the prior deploy.

### Frontend rollback

GitHub Pages serves the latest deploy. To roll back, deploy the previous commit:

```bash
git revert HEAD --no-edit
git push origin main
```

The revert triggers `deploy-frontend.yml` and re-publishes the previous version. Slower than backend rollback (~3 min) but reliable.

For a faster rollback, manually re-trigger an older successful deploy run via Actions → deploy-frontend → Re-run.

## Demo day deployment plan

The morning of demo:

1. **Verify both deploys are green.** Run the smoke test commands above.
2. **Capture the current image SHAs** for both backend and frontend. Write them on a sticky note. If anything breaks during the demo, you have a known-good rollback target.
3. **Do not deploy anything new after T-2 hours.** Even small changes can introduce surprise bugs. Freeze.
4. **Have the local laptop ready as fallback.** If both deploys fail simultaneously (unlikely), you can demo on `localhost:3000` against `localhost:8080` — pre-tested per `docs/TESTING.md` §4 S6.

## Troubleshooting

### `deploy-backend.yml` fails on "Build and push image"

Most common: `IBM_CLOUD_API_KEY` lacks `Editor` on Container Registry.

```bash
ibmcloud iam user-policy-create $YOUR_EMAIL \
  --service-name container-registry --role Manager
```

### Code Engine app is unreachable after deploy succeeded

- Check `ibmcloud ce app get --name helios-backend` → look for `Status: Ready`.
- If status is `Failed`, check the latest revision logs: `ibmcloud ce revision logs --app helios-backend --revision <name>`.
- Most common cause of failure: missing runtime env var (Cloudant or watsonx). The smoke check `/readyz` will tell you which dependency is unreachable.

### Frontend deploys but shows blank page

Open browser DevTools → Network tab → reload. Look for 404s on `_next/static/...`. Usually means `next.config.js` `basePath` is wrong for the GitHub Pages subpath.

For `https://Golden007-prog.github.io/Helios/`:

```js
// next.config.js
module.exports = {
  output: 'export',
  basePath: '/Helios',
  assetPrefix: '/Helios/',
  trailingSlash: true,
};
```

### CORS errors in browser console

Backend `CORS_ORIGINS` env on Code Engine doesn't include the exact frontend origin. Update with:

```bash
ibmcloud ce app update --name helios-backend \
  --env CORS_ORIGINS=https://Golden007-prog.github.io,http://localhost:3000
```

App restarts automatically.

### WebSocket connects then immediately closes

- Check the JWT in the `?token=` query param is valid (decode at jwt.io).
- Check Code Engine app port matches `8080` (default in our Dockerfile).
- Check the WebSocket URL uses `wss://` not `ws://` for the deployed backend.

## What this doc is NOT

- Not the install walkthrough — that's `docs/INSTALLATION.md`
- Not the workflow files — those are `.github/workflows/*.yml`
- Not the architecture overview — that's `docs/ARCHITECTURE.md`
- Not the security policy — that's `docs/SECURITY.md`

## One sentence

> Two simple GitHub Actions workflows, GitHub-stored deploy secrets, runtime secrets set on Code Engine, smoke-test after every deploy, image-SHA-based rollback when it goes wrong, freeze 2 hours before the demo.
