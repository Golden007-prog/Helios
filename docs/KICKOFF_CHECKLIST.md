# Kickoff Checklist — The First 60 Minutes

When you both sit down on day one, follow this in order. No improvising. The goal is "first PR merged within 2 hours" — anything slower means setup pain compounds for the rest of the hackathon.

If you finish a step and the verification doesn't pass, **stop**. Fix the step before continuing. Skipping forward and "I'll come back to it" is how teams lose Friday afternoon to setup debt.

---

## Pre-flight (5 min)

Both developers, in parallel.

- [ ] IBM Cloud account active, logged in at `cloud.ibm.com`
- [ ] GitHub account active, 2FA enabled
- [ ] Bob IDE installed (`https://bob.ibm.com/docs/ide/installation`)
- [ ] Laptop on power, Wi-Fi confirmed, phone charging
- [ ] Slack/Discord open in a side window for sync
- [ ] Reference docs open in a browser tab: `README.md`, `docs/PHASE_PLAN.md`, `docs/AGENTS.md`

If anyone is missing an account, that person creates it now while the other proceeds.

## 1. Repo setup (10 min)

**One developer (Golden):** create the repo and push the scaffold.

```bash
gh repo create Helios --public --description "AI control plane for z/OS modernization"
git clone https://github.com/Golden007-prog/Helios.git
cd Helios
# scaffold from this repo's outputs (AGENTS.md, .bob/mcp.json, .env.example, docs/, etc.)
git add .
git commit -m "scaffold: docs, MCP config, env template"
git push origin main
```

**Other developer (Sayan):** clone.

```bash
git clone https://github.com/Golden007-prog/Helios.git
cd Helios
```

Both:

- [ ] `git status` clean
- [ ] `cat AGENTS.md` displays — Bob's context file is in place
- [ ] `cat .bob/mcp.json | jq` parses — JSON is valid
- [ ] `.env.example` exists; `.env` does NOT exist yet

## 2. Environment file (5 min)

Both developers, independently. Each creates their own `.env` from the template.

```bash
cp .env.example .env
openssl rand -hex 32
# paste output into JWT_SECRET in .env
export PROJECT_ROOT=$(pwd)
echo "PROJECT_ROOT=$PROJECT_ROOT" >> .env
```

Other variables come from the next step. For now:

- [ ] `.env` exists in your local clone
- [ ] `.env` is NOT in `git status`
- [ ] `JWT_SECRET` has a real 64-character hex string
- [ ] `PROJECT_ROOT` is your absolute repo path

## 3. IBM Cloud provisioning (15 min)

**Golden runs this once.** Sayan watches and gets read access.

```bash
ibmcloud login --sso
ibmcloud target -r us-south -g Default

# Cloudant Lite (free)
ibmcloud resource service-instance-create helios-cloudant cloudantnosqldb lite us-south
ibmcloud resource service-key-create helios-cloudant-key Manager --instance-name helios-cloudant
ibmcloud resource service-key helios-cloudant-key
# → copy `url` to CLOUDANT_URL and `apikey` to CLOUDANT_APIKEY in BOTH .env files

# watsonx.ai project — UI only
# 1. Visit https://dataplatform.cloud.ibm.com/
# 2. Create project "Helios", region us-south
# 3. Settings → Services & integrations → Associate watsonx.ai
# 4. Settings → Credentials → copy project_id → WATSONX_PROJECT_ID
# 5. Generate API key → WATSONX_APIKEY
# 6. Models tab → confirm Granite Code 8B and Granite-3-8B-Instruct are listed

# Code Engine project (free tier)
ibmcloud ce project create --name helios-prod
ibmcloud ce project select --name helios-prod
```

Both `.env` files now have:

- [ ] `IBM_CLOUD_API_KEY` (use the same key for both devs in the demo; rotate post-hackathon)
- [ ] `CLOUDANT_URL`, `CLOUDANT_APIKEY`
- [ ] `WATSONX_PROJECT_ID`, `WATSONX_APIKEY`
- [ ] `IBM_CLOUD_REGION=us-south`

Verify:

```bash
curl -fsS -u "apikey:$CLOUDANT_APIKEY" "$CLOUDANT_URL"
# → should return {"couchdb":"Welcome", ...}
```

If 401, your apikey is wrong — recreate the service key as `Manager`, not `Reader`.

## 4. GitHub PAT (5 min)

Both developers, independently.

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token, scopes: `repo`, `read:org`, `read:project`. Expires in 90 days.
3. Copy to `GITHUB_PERSONAL_ACCESS_TOKEN` in your `.env`.

Verify Bob can use it:

```bash
gh auth status
# → "Logged in to github.com as <you>" with the same token
```

- [ ] Both devs have working `gh auth status`
- [ ] PAT has no extra scopes (no `delete_repo`, no `admin:org`)

## 5. Bob IDE setup (10 min)

Both developers.

1. Open Bob IDE → File → Open Folder → select the Helios repo root
2. Open the MCP panel (⚙ → MCP)
3. Confirm green dots on the four enabled servers: `github`, `filesystem`, `memory`, `fetch`
4. Custom servers (`ibm-cloud`, `cloudant`, `watsonx`, `helios-corpus`) show as disabled — **leave them off until they exist** (see `docs/PHASE_PLAN.md`)

Set Bob defaults — Settings panel:

- [ ] Mode: **Plan**
- [ ] Auto-approve: Read ✓, Write ✓, Question ✗, Execute ✗, MCP ✓ (alwaysAllow only)
- [ ] Editor → Code completion: **OFF**
- [ ] Memory MCP: enabled

If MCP servers show red dots, see `docs/MCP_SETUP.md` § Troubleshooting. Most common cause: env vars not inherited — quit Bob, re-source your shell rc, restart Bob (on macOS, `open -a "Bob IDE"` from Terminal).

**Golden additionally:** install Claude Code as silent backup. Copy `docs/templates/CLAUDE.md.template` to `CLAUDE.md` (gitignored). Read the rules.

## 6. Smoke test (10 min)

The repo doesn't have working code yet — that's fine. Smoke-test the *infrastructure* in two ways.

**A. Cloudant round-trip:**

```bash
curl -fsS -u "apikey:$CLOUDANT_APIKEY" -X PUT "$CLOUDANT_URL/helios_smoke_test"
curl -fsS -u "apikey:$CLOUDANT_APIKEY" -X POST "$CLOUDANT_URL/helios_smoke_test" \
  -H "Content-Type: application/json" \
  -d '{"hello":"world"}'
curl -fsS -u "apikey:$CLOUDANT_APIKEY" -X DELETE "$CLOUDANT_URL/helios_smoke_test"
```

All three should return success JSON. If they don't, your IBM Cloud setup has an issue — fix before proceeding.

**B. watsonx.ai round-trip:**

In Bob, open a new task and ask:

> "Use the fetch MCP to call the watsonx.ai inference endpoint with a one-token prompt. Use my .env for credentials."

Bob should produce a working `curl` against `${WATSONX_URL}/ml/v1/text/generation?version=2024-05-31` and report back a model output. If the call fails with `404 model not found`, the model isn't deployed in your project — go back to the dataplatform UI and verify.

- [ ] Cloudant write/read/delete works
- [ ] watsonx generates a token (any token)

## 7. First sync (5 min)

Both developers, side by side.

- [ ] Each shows the other their Bob IDE — green dots match
- [ ] Each confirms their `.env` has the same Cloudant + watsonx + IBM Cloud values
- [ ] Each does NOT have the other's `JWT_SECRET` (those are personal)
- [ ] Read `docs/PHASE_PLAN.md` together — pick the first ticket from Phase 1.1

Divide the first ticket. Golden takes the backend half (`audit_writer.py` + Cloudant indexes), Sayan takes the frontend half (Next.js scaffold + shared design tokens). Branch names:

```bash
# Golden
git checkout -b feat/audit-writer

# Sayan
git checkout -b feat/frontend-scaffold
```

## You're done with kickoff when…

All of these are true. If any is false, **fix that one before writing code**.

- [ ] Both `.env` files are populated and out of git
- [ ] Bob IDE shows 4 green MCP dots on both laptops
- [ ] Cloudant and watsonx both respond to test calls
- [ ] Both devs are on a feature branch with a clear scope
- [ ] You agree on what "done" looks like for the first PR
- [ ] You've scheduled the next sync (15-min, in ~90 min from now)

If you hit hour 2 without a first PR opened, **stop and re-read this checklist**. The wall is almost always a misset env var, not a missing skill.

## What this checklist is NOT

- Not the daily ritual — that's `docs/WORKFLOW.md`
- Not the deploy walkthrough — that's `docs/DEPLOYMENT.md`
- Not the MCP deep-dive — that's `docs/MCP_SETUP.md`
- Not the build sequence — that's `docs/PHASE_PLAN.md`

Tape this checklist next to your laptop. Cross things off with a pen. Setup pain compounds; setup discipline compounds harder.
