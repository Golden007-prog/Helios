# Tools and Services

Every account, service, library, and version Helios depends on. If it's not in this file, you don't need it. If it's in this file, you do.

Cost target: **$0 out-of-pocket through demo day.** Forecast at the bottom.

---

## IBM Cloud

### Cloudant Lite

- **Free tier:** 1 GB storage, 20 reads/sec, 10 writes/sec, no automated backups
- **What we use it for:** all Helios state — regions, audit log, learning signals, runbooks, JCL artifacts
- **Why it fits:** MeridianBank corpus + Helios state stays under 100 MB; 20 RPS reads handles demo concurrency easily
- **Region:** `us-south` (matches watsonx and Code Engine)
- **Provisioning:** `ibmcloud resource service-instance-create helios-cloudant cloudantnosqldb lite us-south`
- **Risk:** rate-limit on demo day if multiple judges hit simultaneously. Mitigation in `docs/TESTING.md` §4 S2.

### watsonx.ai

- **Free trial:** 50,000 token-equivalents per month, refreshes monthly during trial period
- **What we use it for:** Granite Code 8B (COBOL summarization, ABEND explanation) and Granite-3-8B-Instruct (general explanations)
- **Why these models:** Granite Code is purpose-built for code understanding; both are IBM-native (good signal at IBM hackathon)
- **Region:** `us-south.ml.cloud.ibm.com`
- **Provisioning:** UI only at `dataplatform.cloud.ibm.com` (CLI is awkward for project-bound services)
- **Cost beyond free trial:** ~$0.0006 per 1k input tokens, ~$0.0024 per 1k output tokens for Granite Code. Demo-day total < $1 even with heavy use.
- **Risk:** rate-limited or unreachable on demo day. Mitigation: `HELIOS_MOCK_WATSONX=1` returns canned responses, demo stays pixel-identical (`docs/INSTALLATION.md` §10).

### Code Engine

- **Free tier:** 100,000 vCPU-seconds/month, 200,000 GB-seconds memory/month, 100 GB egress
- **What we use it for:** FastAPI backend (autoscale 0-5)
- **Why scale-to-zero:** demo isn't always running; we don't pay when idle
- **Region:** `us-south`
- **Provisioning:** `ibmcloud ce project create --name helios-prod`
- **Memory/CPU:** 1 GB / 1 vCPU per instance — sufficient for demo
- **Cost beyond free tier:** unlikely to hit ceiling during hackathon

### Container Registry (IBM Cloud)

- **Free tier:** 500 MB storage, 5 GB pull traffic/month
- **What we use it for:** the backend container image, pushed by `deploy-backend.yml`
- **Region:** `us-south` (matches Code Engine for free pulls)
- **Provisioning:** automatic on first `ibmcloud cr login`

### IAM API key

- **Cost:** free
- **What we use it for:** authenticating CI deploys, Bob's `ibm-cloud` MCP, backend's Cloudant + watsonx clients
- **Scope:** `Manager` on Cloudant, `Editor` on watsonx project, `Editor` on Code Engine, `Reader` on Container Registry
- **Rotation:** every 90 days; pre-hackathon and post-hackathon

## GitHub

### Account + repo

- **Cost:** free
- **What we use it for:** source of truth, GitHub Actions for CI + deploys, Pages for frontend
- **Visibility:** public — Apache 2.0 license, no shame in showing the code

### Pages

- **Free tier:** unlimited bandwidth on public repos, 1 GB site size, 100 GB/month soft bandwidth limit
- **What we use it for:** static Next.js export of the frontend
- **Provisioning:** Settings → Pages → Source: GitHub Actions (the `deploy-frontend.yml` workflow handles the rest)
- **Custom domain:** optional; demo URL is fine on `*.github.io` for the hackathon

### Personal Access Token (PAT)

- **Cost:** free
- **Scopes:** `repo`, `read:org`, `read:project`. **Do not** add `delete_repo`, `admin:org`, or `workflow` — none are needed.
- **What we use it for:** Bob's `github` MCP, local `gh` CLI
- **Storage:** in each developer's `.env` only. Never in code, never in `.bob/mcp.json`.
- **Rotation:** every 90 days (GitHub default)

### GitHub Actions

- **Free tier:** 2,000 minutes/month for public repos, unlimited concurrency
- **What we use it for:** `ci.yml` (every PR), `deploy-backend.yml` (push to main), `deploy-frontend.yml` (push to main)
- **Cost:** zero — public repo, well under free tier

## Bob IDE

- **Cost:** included with hackathon team allocation (80 Bobcoins per dev)
- **Version:** 1.2.0+ (older versions don't support our MCP config schema)
- **Per-dev coin pool:** see `docs/BOBCOIN_BUDGET.md`
- **License:** team license; not transferable post-hackathon without re-licensing

## Claude Code (Golden only)

- **Cost:** Golden's personal Anthropic account, ~$20/month Pro plan covers hackathon
- **What we use it for:** silent backup when Bob hits a wall on backend complexity
- **Rules:** read `docs/templates/CLAUDE.md.template`. No co-author trailers, no Claude references in code.
- **Sayan does NOT use Claude Code.** Two IDEs on the same frontend codebase causes merge churn.

## Backend libraries

Pinned in `backend/requirements.txt`. Versions chosen for stability, not bleeding edge.

| Library | Version | Why |
|---|---|---|
| `fastapi` | 0.115.* | API framework, OpenAPI auto-gen |
| `uvicorn[standard]` | 0.32.* | ASGI server, WebSocket support |
| `pydantic` | 2.9.* | Request/response validation |
| `ibmcloudant` | 0.9.* | IBM-supplied Cloudant client |
| `ibm-watsonx-ai` | 1.1.* | IBM-supplied watsonx SDK |
| `httpx` | 0.27.* | Outbound HTTP, async |
| `python-jose[cryptography]` | 3.3.* | JWT signing/verifying |
| `python-multipart` | 0.0.* | Form data handling |
| `pyyaml` | 6.0.* | Region profile YAML parsing |
| `ulid-py` | 1.1.* | ULID generation for `_id` fields |
| `structlog` | 24.* | Structured logging |
| `pytest` | 8.* | Tests |
| `pytest-asyncio` | 0.24.* | Async tests |
| `pytest-cov` | 5.* | Coverage |
| `ruff` | 0.7.* | Lint + format |
| `mypy` | 1.13.* | Type checking |

## Frontend libraries

Pinned in `frontend/package.json`.

| Library | Version | Why |
|---|---|---|
| `next` | 14.2.* | App Router, static export |
| `react` | 18.3.* | Required by Next |
| `typescript` | 5.5.* | Type safety |
| `tailwindcss` | 3.4.* | Styling |
| `@monaco-editor/react` | 4.6.* | Diff viewer for Region Atlas + Promote |
| `recharts` | 2.13.* | Confidence Score gauge |
| `lucide-react` | 0.460.* | Icons |
| `clsx` + `tailwind-merge` | latest | Class composition |
| `zod` | 3.23.* | Frontend-side response validation |
| `swr` | 2.2.* | Data fetching with cache |
| `@playwright/test` | 1.48.* | E2E tests |
| `vitest` | 2.1.* | Unit tests |
| `eslint` | 9.* | Lint |

## Local dev tools

| Tool | Min version | Notes |
|---|---|---|
| Node.js | 20.0+ | Frontend build, MCP servers |
| Python | 3.11+ | Backend |
| `uv` | 0.4+ | Python package manager (faster than pip) |
| Git | 2.40+ | Version control |
| `gh` CLI | 2.50+ | GitHub from terminal |
| `ibmcloud` CLI | 2.20+ | IBM Cloud from terminal |
| `jq` | 1.6+ | JSON processing in smoke tests |
| Docker | 24+ | Optional, for local Cloudant alternative |
| `make` | any | Convenience targets |

## Free tier ceilings — what to watch

If any of these get close, we adjust:

| Resource | Limit | Demo day usage estimate | Headroom |
|---|---|---|---|
| Cloudant storage | 1 GB | < 100 MB | 10× |
| Cloudant reads | 20/sec | ~5/sec peak | 4× |
| Cloudant writes | 10/sec | ~2/sec peak | 5× |
| watsonx tokens | 50k/month free trial | ~10k for demo + dev | 5× |
| Code Engine vCPU-sec | 100k/month | ~5k | 20× |
| Container Registry storage | 500 MB | ~150 MB image | 3× |
| GitHub Actions minutes | 2k/month | ~500 minutes | 4× |
| GitHub Pages bandwidth | 100 GB/month soft | ~5 GB | 20× |

The tightest is Cloudant reads/sec. Mitigation: in-memory cache for hot reads (`backend/services/cache.py`).

## Cost forecast — demo day

| Line item | Cost |
|---|---|
| IBM Cloud Cloudant | $0 (Lite) |
| IBM Cloud watsonx | $0 (free trial) |
| IBM Cloud Code Engine | $0 (free tier) |
| IBM Container Registry | $0 (free tier) |
| GitHub | $0 (public repo) |
| Bob IDE | $0 (team allocation) |
| Claude Code (Golden) | ~$5 attributable to hackathon (~weekly portion of monthly Pro) |
| Domain | $0 (using `*.github.io`) |
| **Total out-of-pocket** | **~$5** |

Phase 2 pilot ranges $200-$500/month per shop, mostly driven by audit log volume and watsonx tokens (`docs/ROADMAP.md`).

## What we deliberately do NOT use

| Tool | Why not |
|---|---|
| Postgres | Document-shaped data, want `_changes` feed; see `docs/DATA_MODEL.md` §14 |
| Redis | Cloudant + in-memory cache covers our needs; one less service to provision |
| Kafka / Event Hub | Cloudant `_changes` feed is the event stream we need |
| Auth0 / Okta | Hackathon uses seeded JWT; SSO is Phase 2 |
| Datadog / New Relic | Code Engine logs + structlog are sufficient; observability is Phase 2 |
| AWS / GCP / Azure | All-IBM stack scores at IBM hackathon |
| Terraform | Manual provisioning is faster for 4 services; IaC is Phase 2 |
| Mistral / Llama | Granite is the IBM model family |
| Vector store | Learning Loop is labeled retrieval, not embedding similarity (`docs/LEARNING_LOOP.md`) |

## Provisioning cheat sheet

For someone setting up from zero. Each line is a single command or UI action.

```bash
# 1. IBM Cloud
ibmcloud login --sso
ibmcloud target -r us-south -g Default
ibmcloud resource service-instance-create helios-cloudant cloudantnosqldb lite us-south
ibmcloud resource service-key-create helios-cloudant-key Manager --instance-name helios-cloudant
ibmcloud ce project create --name helios-prod
ibmcloud cr namespace-add helios

# 2. watsonx (UI)
# - dataplatform.cloud.ibm.com → New project "Helios", region us-south
# - Settings → Services & integrations → Associate watsonx.ai
# - Models → confirm Granite Code 8B + Granite-3-8B-Instruct

# 3. GitHub (UI)
# - Create public repo Helios
# - Settings → Pages → Source: GitHub Actions
# - Settings → Secrets → Actions → add IBM_CLOUD_API_KEY, NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_WS_URL

# 4. Local
git clone https://github.com/<you>/Helios.git
cd Helios && cp .env.example .env  # then fill in
```

Total: ~25 minutes for a fresh environment.

## What this file is NOT

- Not the kickoff checklist — that's `docs/KICKOFF_CHECKLIST.md`
- Not the deployment guide — that's `docs/DEPLOYMENT.md`
- Not the architecture overview — that's `docs/ARCHITECTURE.md`
- Not the security policy — that's `docs/SECURITY.md`
