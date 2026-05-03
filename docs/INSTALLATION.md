# Local Installation

How to get Helios running on your laptop in under 30 minutes. This is the first thing a new contributor reads.

If you only want to deploy to IBM Code Engine, read `docs/DEPLOYMENT.md` instead.

---

## Pre-flight

You need:

| Requirement | Why | How to verify |
|---|---|---|
| Git | Clone the repo | `git --version` |
| Node.js 20+ | Frontend build | `node --version` |
| Python 3.11+ | Backend | `python --version` |
| `uv` (or `pip`) | Python deps | `uv --version` |
| Docker (optional) | Local Cloudant alternative for offline dev | `docker --version` |
| IBM Cloud account | Cloudant + watsonx + Code Engine | Logged in at cloud.ibm.com |
| Bob IDE | Primary developer experience | https://bob.ibm.com/docs/ide/installation |
| GitHub account | Push branches | `gh auth status` |

You do NOT need:

- A real mainframe — the MeridianBank synthetic corpus is bundled.
- Zowe — only needed for real-mainframe ops, post-hackathon.
- A Mistral or Llama subscription — only Granite models are used.

## 1. Clone

```bash
git clone https://github.com/Golden007-prog/Helios.git
cd Helios
```

## 2. Bring up the corpus

The MeridianBank synthetic shop is recreated locally from upstream OSS COBOL projects. It does not ship in the repo (license cleanliness).

```bash
cd shared/sample-corpus
./_seed.sh
cd ../..
```

Takes ~90 seconds. Produces `shared/sample-corpus/MERIDIANBANK/` with ~14 MB of COBOL, JCL, copybooks, region YAMLs, and seed data.

Verify:
```bash
sha256sum -c shared/sample-corpus/corpus.sha256
```

If the hash differs, your network fetched a different upstream version. Open an issue, do not proceed.

## 3. Provision IBM Cloud services

You need three services in IBM Cloud, all free-tier:

```bash
# Login
ibmcloud login --sso
ibmcloud target -r us-south -g Default

# Cloudant Lite
ibmcloud resource service-instance-create helios-cloudant cloudantnosqldb lite us-south
ibmcloud resource service-key-create helios-cloudant-key Manager --instance-name helios-cloudant
ibmcloud resource service-key helios-cloudant-key  # copy url + apikey to .env

# watsonx.ai project — easier via UI
# 1. Visit https://dataplatform.cloud.ibm.com/
# 2. Create a project, region us-south
# 3. Associate the project with watsonx.ai
# 4. Settings → Credentials → copy project_id and create an API key
# 5. Confirm Granite Code 8B and Granite-3-8B-Instruct are listed under Models

# Code Engine project (only needed for deploy; skip for pure local dev)
ibmcloud ce project create --name helios-prod
ibmcloud ce project select --name helios-prod
```

## 4. Configure environment

```bash
cp .env.example .env
$EDITOR .env   # fill in IBM_CLOUD_API_KEY, WATSONX_*, CLOUDANT_*, JWT_SECRET, GITHUB_PERSONAL_ACCESS_TOKEN
```

The `JWT_SECRET` should be unique per developer:

```bash
openssl rand -hex 32   # paste into .env as JWT_SECRET
```

Never commit your `.env`. The repo's `.gitignore` already covers it; do not "fix" the exclusion.

## 5. Backend

```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
python migrations/apply_indexes.py   # creates Cloudant collections + indexes
python migrations/seed_data.py       # loads MeridianBank seeds + users
uvicorn api.main:app --reload --port 8080
```

Verify:

```bash
curl http://localhost:8080/healthz
# {"ok":true,"data":{"version":"...","ts":"..."}}

curl http://localhost:8080/readyz
# {"ok":true,"data":{"cloudant":"reachable","watsonx":"reachable"}}
```

If `readyz` fails, the error names which dependency is unreachable. Most common: wrong `WATSONX_URL` (must be `https://us-south.ml.cloud.ibm.com`) or expired `IBM_CLOUD_API_KEY`.

## 6. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`. Login with `maya@meridianbank.demo` / `helios2026` (seeded credentials from §2).

## 7. Bob IDE

```bash
# In the project root
code .   # or open Bob IDE → Open Folder → select Helios root
```

Bob auto-detects `.bob/mcp.json`. Open the MCP panel (gear icon → MCP); confirm the four enabled servers (`github`, `filesystem`, `memory`, `fetch`) show green dots. The four custom Helios servers (`ibm-cloud`, `cloudant`, `watsonx`, `helios-corpus`) are disabled by default — enable them as you build them.

Set Bob defaults to match the team:
- Mode: Plan
- Auto-approve: Read ✓, Write ✓, Question ✗, Execute ✗, MCP ✓ (alwaysAllow list only)
- Editor → Code completion: OFF (saves Bobcoins)

If you are Golden, also install Claude Code as silent backup. See `docs/templates/CLAUDE.md.template` for ground rules — never commit AI co-author trailers, never reference Claude in code/comments/docs.

## 8. First test — round-trip the demo

In the Helios UI:

1. Navigate to **Atlas** → click `int2` → click **Diff with int3**. Should show 7 highlighted differences.
2. Navigate to **Studio** → open `CUST_DELETE_INACTIVE.JCL` (region `int2`) → click **Promote to int3**. Should show diff, score 62/RED, three top reasons.
3. Click **Auto-fix the backup gap**. Score → 94/GREEN.
4. Click the copybook drift finding → **Auto-fix**. Score → 100/GREEN.
5. Click **Promote**. State → `pending_review`.
6. Open a second browser tab, login as `anil`. The Review Queue badge should show `(1)`. Click **Approve**.
7. First tab toast: *"Anil approved your promote, completed at HH:MM:SS"*.
8. Navigate to **Audit** → search `CUST_DELETE_INACTIVE` → see two events (the request and the approval).

If all eight steps work, your local Helios is healthy. If any fails, check `request_id` in the toast / response and grep backend logs for it.

## 9. Common issues

### `cloudant: 401 Unauthorized` on first request

Your `CLOUDANT_APIKEY` is wrong, OR your service key has Reader access only. Recreate the key as Manager:

```bash
ibmcloud resource service-key-delete helios-cloudant-key
ibmcloud resource service-key-create helios-cloudant-key Manager --instance-name helios-cloudant
```

### `watsonx: model 'ibm/granite-code-8b-instruct' not found in this project`

The project does not have watsonx.ai enabled or the model is not deployed there. Visit the watsonx project, Settings → Services & integrations → ensure watsonx.ai is associated; visit Models and verify the Granite Code 8B is listed (deploy if not).

### Frontend gets CORS errors

Backend `.env` `CORS_ORIGINS` must include `http://localhost:3000`. Restart the backend after editing.

### Bob IDE shows red dots for MCP servers

Most often: `GITHUB_PERSONAL_ACCESS_TOKEN` not exported to the shell Bob inherited. Quit Bob fully, re-source your shell rc file, restart Bob. On macOS, you may need to launch Bob from Terminal (`open -a "Bob IDE"`) to inherit the env.

### `uv` not found

Install: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv` in any Python).

### MeridianBank corpus hash mismatch

Upstream changed. Pin the `_cache/` URLs in `shared/sample-corpus/_seed.sh` to the SHA-pinned versions documented in `docs/CORPUS.md`. Open an issue.

## 10. Offline development (no IBM Cloud)

For pure-frontend or pure-backend work without IBM Cloud:

```bash
# Local Cloudant via Docker (CouchDB is API-compatible enough)
docker run -d --name helios-couch \
  -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=admin \
  -p 5984:5984 couchdb:3

# In .env
CLOUDANT_URL=http://admin:admin@localhost:5984
CLOUDANT_APIKEY=  # leave blank; basic auth used in URL

# Stub watsonx with a mock returning canned Granite responses
HELIOS_MOCK_WATSONX=1
```

The mock layer lives in `backend/services/watsonx_client.py` behind the `HELIOS_MOCK_WATSONX` feature flag. It returns the demo's pre-recorded responses verbatim, so the demo remains pixel-identical even with no internet.

## 11. Tearing down

```bash
# Stop services
pkill -f uvicorn
pkill -f "next dev"
docker stop helios-couch && docker rm helios-couch  # if you used it

# Wipe local state (keeps your .env)
rm -rf shared/sample-corpus/_cache shared/sample-corpus/MERIDIANBANK
```

To delete IBM Cloud resources:

```bash
ibmcloud resource service-instance-delete helios-cloudant
ibmcloud ce project delete --name helios-prod
```

(watsonx.ai projects are deleted from the dataplatform UI.)

## 12. What good looks like — installation done

You can answer yes to all of these:

- `curl localhost:8080/readyz` returns `{"ok":true}` with both dependencies reachable
- The Helios UI loads at `localhost:3000` and you can log in as Maya
- A round-trip promote-and-approve completes between two browser tabs
- The audit log shows the events
- Bob IDE shows green dots for the four enabled MCP servers
- Your `.env` is NOT in `git status`

If any of these is no, fix that one before moving on. Skipping setup pain compounds.
