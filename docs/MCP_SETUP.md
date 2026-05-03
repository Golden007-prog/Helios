# MCP Setup — Bob IDE Configuration

How Bob talks to GitHub, the filesystem, IBM Cloud, Cloudant, watsonx, and the MeridianBank corpus. The shared config lives in `.bob/mcp.json` (committed to the repo); per-developer credentials live in `.env` (gitignored). Bob inherits both at launch.

If something feels off about MCP, 90% of the time it's that Bob inherited the wrong shell environment. See § Troubleshooting.

---

## The two-layer model

| Layer | What's in it | Where it lives |
|---|---|---|
| Shared config | Server names, commands, args, alwaysAllow rules | `.bob/mcp.json` (committed) |
| Per-dev secrets | API keys, tokens, paths | `.env` (gitignored) |

The shared config uses `${VAR_NAME}` substitution to pull values from the environment. This means: same `.bob/mcp.json` works for both developers; only their `.env` files differ.

## The seven servers

Four enabled out of the box, three custom Helios servers disabled until built.

### Enabled by default

#### `github`

Reads issues, PRs, commits, file contents directly from GitHub without manual `gh` calls. Used constantly during planning ("what does PR #34 look like" / "is there an issue tagged audit-bug").

- Package: `@modelcontextprotocol/server-github` (npx, no install)
- Auth: `GITHUB_PERSONAL_ACCESS_TOKEN` from `.env`
- Scope: classic PAT with `repo`, `read:org`, `read:project`. No `delete_repo`, no `admin:*`.
- alwaysAllow: read-only operations (`search_repositories`, `get_file_contents`, etc.)

Write operations (creating issues, opening PRs) are NOT in alwaysAllow — Bob asks before each one.

#### `filesystem`

Reads files in the repo. The most-used MCP after a while because it's how Bob navigates without burning coins on `cat` calls.

- Package: `@modelcontextprotocol/server-filesystem`
- Scope: rooted at `${PROJECT_ROOT}` — Bob cannot read outside the repo
- alwaysAllow: read-only

The filesystem MCP does not write files. Writes go through Bob's normal write tools, which respect Bob's auto-approve settings.

#### `memory`

Cross-session continuity. Bob remembers project conventions, naming choices, and decisions across tasks within the same workspace.

- Package: `@modelcontextprotocol/server-memory`
- Storage: local SQLite under `~/.bob/memory/`
- alwaysAllow: read operations

Memory is per-developer. Golden's memory does not bleed into Sayan's. Reset with `rm ~/.bob/memory/helios.db`.

#### `fetch`

HTTP GET for arbitrary URLs. Used to read external docs (IBM Cloud reference, Granite model cards, Cloudant API docs) without leaving the IDE.

- Package: `@modelcontextprotocol/server-fetch`
- alwaysAllow: `fetch`

This server has no auth and no scope — it can fetch anything Bob asks it to. That's intentional; the tradeoff is "can't read your private GitHub" (use the github MCP for that).

### Custom Helios servers (disabled until built)

These are project-local Python servers under `backend/mcp/`. They expose Helios-specific operations to Bob. **Build order matches the phases in `docs/PHASE_PLAN.md`:**

| Server | Phase | Purpose |
|---|---|---|
| `helios-corpus` | 1.1 | Read JCL/COBOL/region YAMLs from `shared/sample-corpus/MERIDIANBANK/`. First custom server because it has no IBM Cloud dependency. |
| `cloudant` | 1.1 | Read-only Cloudant queries scoped to `helios_*` collections. Used during dev to inspect state. |
| `ibm-cloud` | 1.6 | Read-only IBM Cloud resource queries (Code Engine app status, Cloudant usage). Useful in deployment phase. |
| `watsonx` | 1.4 | Wraps Granite Code calls with shop-aware prompt templates. Not strictly needed (the backend can call watsonx directly) but speeds Bob's iteration on prompt tweaks. |

Each custom server gets its own short doc under `backend/mcp/SERVER_NAME.md` when built. The shared template is in `backend/mcp/SERVER_TEMPLATE.md`.

## Configuration walkthrough

### `.bob/mcp.json` structure

The file is committed at the repo root under `.bob/`. Bob auto-detects it on workspace open.

Top-level fields:

| Field | Purpose |
|---|---|
| `version` | Schema version. Pin to `1` until Bob 2.x. |
| `comment` | Free-form note for humans. Bob ignores it. |
| `servers` | Map of server name → config. |

Per-server fields:

| Field | Purpose |
|---|---|
| `enabled` | If `false`, Bob doesn't try to start it. |
| `command` + `args` | Process to launch. Stdio MCP. |
| `env` | Map of env vars passed to the server. Use `${VAR}` to pull from Bob's environment. |
| `alwaysAllow` | List of tool names Bob can invoke without confirmation. |
| `comment` | Note for humans. |

### Per-developer `.env`

Bob inherits the shell environment it was launched from. Variables Bob needs:

```bash
PROJECT_ROOT=/Users/golden/dev/Helios
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
IBM_CLOUD_API_KEY=...
IBM_CLOUD_REGION=us-south
CLOUDANT_URL=https://...cloudantnosqldb.appdomain.cloud
CLOUDANT_APIKEY=...
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=...
WATSONX_APIKEY=...
```

Source these in your shell rc (`~/.zshrc` or `~/.bashrc`):

```bash
# Helios — auto-load .env when entering the repo
helios-load() {
  if [ -f .env ]; then
    set -a; source .env; set +a
    echo "Helios env loaded ($(wc -l < .env) vars)"
  fi
}
chpwd_functions+=(helios-load)
helios-load
```

Restart your shell. `cd ~/dev/Helios` should print "Helios env loaded".

### Launching Bob with the right env

Three ways, ranked by reliability:

1. **Best: launch from a terminal that has the env loaded.**
   ```bash
   cd ~/dev/Helios
   open -a "Bob IDE" .   # macOS
   bob .                  # Linux
   ```

2. **Acceptable: macOS launchd plist.** Persists env vars across logins, but a pain to update. Only do this if Bob is your default IDE for everything.

3. **Bad: launching from Spotlight / Start Menu and hoping.** GUI-launched Bob does not inherit interactive shell env on macOS. MCP servers will appear red.

## alwaysAllow — what's safe to auto-approve

The principle: **read = auto, write = ask, execute = always ask.**

| Operation class | Auto-approve? |
|---|---|
| Reading repo files | ✅ |
| Reading GitHub issues/PRs | ✅ |
| Searching memory graph | ✅ |
| HTTP GET (fetch) | ✅ |
| Reading Cloudant docs (custom MCP) | ✅ |
| Reading corpus files (custom MCP) | ✅ |
| Writing repo files | ⚠️ Bob's writeFile tool respects mode |
| Creating GitHub issues | ❌ ask |
| Calling watsonx (costs $) | ❌ ask |
| Writing to Cloudant | ❌ ask |
| Running shell commands | ❌ ask |

If you find Bob is asking too many times for the same safe op, add it to `alwaysAllow` — but only for read operations. Adding writes to alwaysAllow defeats the whole point of plan mode.

## Claude Code (Golden's silent backup)

Golden additionally runs Claude Code as a sidecar for the moments when Bob runs out of coins or hits a wall on a complex backend task. Rules:

- Claude Code reads `CLAUDE.md` (gitignored, copied from `docs/templates/CLAUDE.md.template`).
- Claude Code uses the same MCP servers via the same `.bob/mcp.json` (Claude Code reads the file).
- Claude Code outputs are reviewed and re-committed by Golden — never directly merged.
- No "Co-authored-by" trailers. No comments referencing Claude. The work is Golden's.

Sayan does not run Claude Code. The team needs one source of truth on the frontend, and dual-IDE on the same code path causes merge churn that costs more than it saves.

## Troubleshooting

### Red dots on the four default MCP servers

- **Most common:** `GITHUB_PERSONAL_ACCESS_TOKEN` not in Bob's environment. Verify with `env | grep GITHUB` in the same terminal you launched Bob from. If empty, your `.env` isn't being sourced.
- **Second most common:** `npx` not on PATH. Bob shells out to `npx`; if your shell doesn't have it, the MCP fails. Install Node.js 20+ globally.
- **Third:** firewall blocking `npm` registry. The MCP servers are downloaded on first use; if download fails, the dot stays red. Check `npm config get registry`.

### Bob IDE → Settings → MCP shows servers but commands fail

Run the command Bob runs, manually:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PERSONAL_ACCESS_TOKEN \
  npx -y @modelcontextprotocol/server-github
```

The error is usually informative. If it complains about the token, the token's scope is insufficient or expired.

### Custom Helios servers won't start

Check that the Python module exists:

```bash
python -m backend.mcp.cloudant_server --help
```

If "no module named", the server isn't built yet. That's expected per `docs/PHASE_PLAN.md` — leave `enabled: false` in the config.

### Bob asks for confirmation on something in alwaysAllow

`alwaysAllow` matches on tool name exactly. Check the spelling against the server's actual tool list (Bob's MCP panel shows them). Common typo: `read_files` instead of `read_file`.

## What this file is NOT

- Not the API contract — that's `docs/API.md`.
- Not the deploy guide — that's `docs/DEPLOYMENT.md`.
- Not the workflow — that's `docs/WORKFLOW.md`.
- Not the coin budget — that's `docs/BOBCOIN_BUDGET.md`.

## Implementation pointers

| Concern | File | Owner |
|---|---|---|
| Shared MCP config | `.bob/mcp.json` | Both, edits via PR |
| Per-dev env loader | each developer's `~/.zshrc` | Personal |
| Custom MCP scaffold | `backend/mcp/SERVER_TEMPLATE.md` | Golden |
| `helios-corpus` MCP | `backend/mcp/corpus_server.py` | Golden, Phase 1.1 |
| `cloudant` MCP | `backend/mcp/cloudant_server.py` | Golden, Phase 1.1 |
| `watsonx` MCP | `backend/mcp/watsonx_server.py` | Golden, Phase 1.4 |
| `ibm-cloud` MCP | `backend/mcp/ibm_cloud_server.py` | Golden, Phase 1.6 |
| Claude Code rules | `CLAUDE.md` (gitignored) | Golden personal |
