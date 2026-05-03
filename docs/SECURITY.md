# Security

How we handle secrets, credentials, and access control during the hackathon. Most of these rules exist because IBM monitors hackathon-provisioned accounts; one leaked key can suspend the whole team.

---

## What counts as a secret

| Category | Examples | Where it goes |
|---|---|---|
| IBM Cloud API key | `IBM_CLOUD_API_KEY` | Shell env var only; Code Engine secret in deploy |
| watsonx.ai API key | `WATSONX_API_KEY` | Shell env var only; Code Engine secret in deploy |
| watsonx project ID | `WATSONX_PROJECT_ID` | Shell env var (less sensitive but still not in repo) |
| Cloudant credentials | `CLOUDANT_URL`, `CLOUDANT_APIKEY` | Shell env var; Code Engine secret in deploy |
| GitHub Personal Access Token | `GITHUB_PERSONAL_ACCESS_TOKEN` | Shell env var only; never in Code Engine |
| Anthropic API key (Golden's Claude Code) | `ANTHROPIC_API_KEY` | Shell env var only; per Golden's machine |

Hard rule: **no secret ever lives in a file that is or could be committed to the repo.**

---

## Where secrets must NOT appear

- `.env` (only `.env.example` is committed; `.env.example` contains placeholders only, never real values)
- `.bob/mcp.json` (uses `${env:VARNAME}` interpolation — never inline values)
- Any `*.json`, `*.yaml`, `*.toml` config in the repo
- Code (no `os.environ['IBM_CLOUD_API_KEY'] = "actual-value"` ever)
- Comments
- Commit messages
- PR descriptions
- Bob session reports (Bob is configured not to log secret env vars but verify on export)
- Screenshots (mask before pasting in PRs or chat)

---

## `.env.example` template

This file IS committed. It contains placeholders only:

```bash
# IBM Cloud — provision via IAM → API keys
IBM_CLOUD_API_KEY=__replace_with_your_ibm_cloud_api_key__
IBM_CLOUD_REGION=us-south

# watsonx.ai — from watsonx.ai project sandbox
WATSONX_API_KEY=__replace_with_your_watsonx_api_key__
WATSONX_PROJECT_ID=__replace_with_your_project_id__
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Cloudant — from Cloudant service credentials
CLOUDANT_URL=https://__instance__.cloudantnosqldb.appdomain.cloud
CLOUDANT_APIKEY=__replace_with_your_cloudant_apikey__

# GitHub — Personal Access Token for MCP
GITHUB_PERSONAL_ACCESS_TOKEN=__replace_with_your_github_pat__

# Optional: Anthropic API key (Golden only, for Claude Code)
# ANTHROPIC_API_KEY=__replace_with_your_anthropic_key__
```

Each developer copies this to `.env` (which IS gitignored) and fills in real values.

---

## How Bob and Claude Code read secrets

Both clients use environment-variable interpolation in their MCP configs. Bob's `.bob/mcp.json` uses `${env:VARNAME}`; Claude Code's `~/.claude/mcp.json` uses the same syntax.

This means:
- The MCP config files contain only the *names* of env vars, not values
- Bob/Claude Code resolve those at runtime from the shell that launched them
- If you launch Bob from a terminal that has env vars set, Bob sees them
- If you launch Bob from the OS application launcher (Spotlight, Start menu), it may not have your shell env — restart from a fresh terminal

---

## GitHub Personal Access Token (PAT) scope

Each developer's PAT (used by the GitHub MCP server):

- **Name:** `helios-bob-mcp-<your-name>`
- **Expiry:** 7 days (covers the hackathon)
- **Scopes:**
  - `repo` (full)
  - `workflow`
  - `read:org`
  - `user`

Do **not** add `admin:org`, `delete_repo`, or any `*:enterprise` scope. Minimal scope reduces blast radius if leaked.

If a PAT is committed accidentally:
1. Rotate within 5 minutes — `Settings → Developer settings → Tokens → Delete`
2. Generate a replacement
3. Update your shell env var
4. Restart Bob (and Claude Code if Golden)
5. Document in commit history: `chore(security): rotate PAT after accidental commit (token already revoked)`

---

## IBM Cloud credentials

### Creation rules

- API keys named `helios-<purpose>-<owner>` (e.g., `helios-bob-mcp-golden`, `helios-deploy-ci`)
- Do not create root-account API keys; use IAM users with restricted policies
- Each API key gets a description noting its purpose

### Rotation

- Rotate any IBM Cloud API key immediately if a commit ever included it
- IBM Cloud's secret scanner reports leaks to Anthropic/IBM; an account flagged this way may be suspended

### Code Engine secrets (production)

The deployed FastAPI app reads credentials as Code Engine secrets, mounted as env vars. Never bake them into the container image.

Deploy script pseudo-code:
```bash
ibmcloud ce secret create --name helios-cloudant \
  --from-literal CLOUDANT_URL="$CLOUDANT_URL" \
  --from-literal CLOUDANT_APIKEY="$CLOUDANT_APIKEY"

ibmcloud ce secret create --name helios-watsonx \
  --from-literal WATSONX_API_KEY="$WATSONX_API_KEY" \
  --from-literal WATSONX_PROJECT_ID="$WATSONX_PROJECT_ID"

ibmcloud ce app update --name helios-backend \
  --env-from-secret helios-cloudant \
  --env-from-secret helios-watsonx
```

The script itself can be in the repo (it reads from your shell env). The values it consumes can never be.

---

## Pre-commit secret scanning

Install `gitleaks` or `detect-secrets`:

```bash
# Option A — gitleaks
brew install gitleaks      # macOS
gitleaks protect --staged  # add to .git/hooks/pre-commit

# Option B — detect-secrets
pip install detect-secrets
detect-secrets scan > .secrets.baseline
```

If the hook flags a commit, abort, remove the offending content, then proceed. Do not bypass with `--no-verify`.

---

## Logs and Bob session reports

Bob's session export writes the conversation to markdown. By default it does not include resolved env var values, but it CAN include them if you typed a credential into chat. Rule:

- Never paste a credential into a Bob (or Claude Code) chat
- If you accidentally do, immediately rotate that credential
- Before committing a `bob_sessions/<owner>/*.md` file, search it for known secret prefixes (`ghp_`, `IBM_CLOUD_`, `WATSONX_`)

A simple grep before commit:
```bash
grep -E "(ghp_|IBM_CLOUD_API_KEY|WATSONX_API_KEY|CLOUDANT_APIKEY)" bob_sessions/<owner>/*.md && echo "STOP — secret detected"
```

---

## Audit trail

Every state-changing action in Helios writes to the Cloudant `audit_log` collection. This is the application-level audit. Schema:

```json
{
  "_id": "auto-generated",
  "timestamp": "2026-05-02T15:34:12Z",
  "actor": "golden",
  "action": "region.update",
  "target": "int3",
  "before": { "<region YAML>" },
  "after": { "<region YAML>" },
  "diff": [ ... ],
  "reason": "user-supplied for overrides; auto for routine actions",
  "helios_version": "0.1.0"
}
```

The audit log is queryable from the Helios UI (Audit tab), exportable to CSV. SOX-ready from day one.

What gets logged:
- Region profile create / update / delete
- JCL promotion (request + outcome)
- Confidence Score override (with reason)
- Auto-backup acceptance / rejection
- ABEND runbook save
- JJSCAN+ finding dismissal (feeds `helios_learning`)

What does NOT get logged:
- Read-only API calls (would flood the log; tracked separately in metrics)
- User credentials (obviously)

---

## Repository access

GitHub repo `https://github.com/Golden007-prog/Helios`:

- **Owner:** Golden (`@Golden007-prog`)
- **Collaborator:** Sayan (`@Sayan1320`) — write access
- **Branch protection on `main`:**
  - Require a pull request before merging
  - Require 1 approval (auto-merge allowed when CI passes)
  - Require status checks: lint, test, build
  - Disable force-pushes
  - Disable branch deletion

After the hackathon, the repo can be made open-source under Apache 2.0. Before that, public visibility is set per IBM hackathon rules.

---

## Incident response

If you suspect a credential has leaked (commit pushed, screenshot shared, log file uploaded somewhere):

1. **Rotate the credential immediately** — do this before anything else
2. Verify the leak is contained (no other clones of the secret in flight)
3. Notify the other team member
4. Document the incident in `docs/RISK_REGISTER.md` under "Closed risks"
5. Update this doc if a new prevention rule is needed

---

## What we explicitly do NOT do (and won't pretend to)

- We do **not** implement enterprise SSO / SAML for Helios in the hackathon scope
- We do **not** implement RBAC inside Helios — every authenticated user has full access in the demo
- We do **not** encrypt the Cloudant data at rest beyond what Cloudant Lite provides natively
- We do **not** provide audit-log tamper-evidence (append-only is enforced by API, not by hash chain)

These are roadmap items. Documenting them honestly is more credible than pretending we shipped enterprise-grade auth in a weekend.
