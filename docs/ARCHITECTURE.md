# Architecture

## System Architecture Diagram

```mermaid
flowchart TB
    subgraph users[Users]
        Maya[Maya<br/>Mainframe Developer]
        Raj[Raj<br/>Reviewer / Lead]
    end

    subgraph frontend[Frontend - GitHub Pages CDN]
        UI[Helios UI<br/>Next.js 14 + Tailwind + shadcn/ui]
        Editor[Monaco Editor<br/>JCL / COBOL syntax]
        Graph[React Flow<br/>Dependency Graph]
        Gauge[Confidence Score Gauge<br/>SVG + D3]
    end

    subgraph backend[Backend - IBM Code Engine]
        API[FastAPI Gateway]
        Atlas[Region Atlas Service]
        JJ[JJSCAN+ Engine]
        ABEND[ABEND Archaeologist]
        Score[Confidence Score Service]
        Audit[Audit Log Writer]
        Review[Review Queue<br/>WebSocket Hub]
    end

    subgraph mcp[MCP Layer]
        BobMCP[Bob IDE MCP Client]
        CCMCP[Claude Code MCP Client<br/>Golden only - silent]
        Custom[Helios Custom MCP Servers<br/>cloudant / watsonx / corpus / ibm-cloud]
    end

    subgraph ibm[IBM Cloud Services]
        Cloudant[(Cloudant Lite<br/>regions / audit_log<br/>helios_learning / abend_patterns)]
        WX[watsonx.ai<br/>Granite Code 8B<br/>Granite-3-8B-Instruct]
        WXO[watsonx Orchestrate<br/>Multi-agent supervisor]
        NLU[NLU<br/>ABEND entity extraction]
    end

    subgraph corpus[Demo Corpus]
        Mer[MeridianBank Synthetic Shop<br/>5 COBOL programs / 3 copybooks<br/>6 region profiles / 2 DB2 tables<br/>10 seeded ABEND incidents]
    end

    Maya --> UI
    Raj --> UI
    UI --> Editor
    UI --> Graph
    UI --> Gauge
    UI <--> API
    Review -.WebSocket.-> UI
    API --> Atlas
    API --> JJ
    API --> ABEND
    API --> Score
    API --> Audit
    API --> Review
    Atlas <--> Cloudant
    JJ --> WX
    ABEND --> WX
    ABEND --> NLU
    ABEND <--> Cloudant
    Score --> Cloudant
    Audit --> Cloudant
    Cloudant -.change feed.-> Review
    BobMCP <--> Custom
    CCMCP <--> Custom
    Custom <--> Cloudant
    Custom <--> WX
    Custom <--> Mer
    WXO --> Atlas
    WXO --> JJ
    WXO --> ABEND
    WXO --> Score
```

## Component breakdown

### Frontend (Sayan)

Single-page Next.js app exported as static HTML, served from GitHub Pages. No SSR — keeps deployment free and trivial.

**Key UI surfaces:**
- **Studio** — JCL / COBOL editor with the region picker, JJSCAN+ panel, Confidence Score gauge
- **Atlas** — region profile manager, side-by-side YAML diff view (this is the hero shot for the demo)
- **Archaeology** — ABEND dump paste box, traced source view, runbook generator
- **Review Queue** — real-time list of pending promotions, WebSocket-driven
- **Audit** — append-only log viewer with filters

**Conventions:**
- Tailwind for styling; shadcn/ui for primitives; lucide-react for icons
- Monaco editor with custom JCL/COBOL syntax definitions (we ship these in `frontend/lib/monaco-langs/`)
- React Flow for dependency graphs; Mermaid for call graphs
- D3 for the Confidence Score gauge (custom SVG, animates on score change)

### Backend (Golden)

FastAPI app on Code Engine. Async throughout — `httpx` for outbound, `aiocouch` for Cloudant, `websockets` for the Review Queue hub.

**Service modules:**
- `services/atlas/` — region profile CRUD, promote-job logic, backup job generator
- `services/jjscan/` — dependency resolver, static rule engine, COBOL/JCL parser glue
- `services/abend/` — pattern matcher, dump parser, COBOL traceback, runbook synthesizer
- `services/score/` — Confidence Score formula, weight loader
- `services/audit/` — append-only writer, query API
- `services/review/` — WebSocket hub, Cloudant change-feed consumer

**Library glue:**
- `proleap-cobol-parser` for COBOL AST (Java; called via subprocess or rewritten as a small companion service)
- `koopa-cobol-parser` as a pure-Python fallback for lighter parsing
- Custom JCL parser (~400 lines, hand-written — JCL is too irregular for off-the-shelf grammars)

### MCP Layer

Two clients, four custom servers.

**Clients:**
- **Bob IDE MCP** — both Golden and Sayan. Reads `.bob/mcp.json` from the workspace.
- **Claude Code MCP** — Golden only, silent backup. Reads `~/.claude/mcp.json` (per-user, not in repo).

**Off-the-shelf servers loaded by both clients:**
- `@modelcontextprotocol/server-github` — repo ops, PRs, issues
- `@modelcontextprotocol/server-filesystem` — sandbox to project folder
- `@modelcontextprotocol/server-memory` — persistent context across Bob sessions
- `mcp-server-fetch` — for pulling open-source COBOL repos and IBM docs

**Custom Helios servers (we build these):**
- `mcp-servers/ibm-cloud/` — wraps `ibmcloud` CLI for one-shot Code Engine and Cloudant ops
- `mcp-servers/cloudant/` — CRUD against Cloudant from inside Bob without leaving the IDE
- `mcp-servers/watsonx/` — direct Granite Code 8B inference for COBOL/JCL tasks
- `mcp-servers/helios-corpus/` — exposes the MeridianBank synthetic shop as a queryable resource

Full setup in [`MCP_SETUP.md`](MCP_SETUP.md).

### IBM Cloud Services

| Service | Tier | Purpose | Cost |
|---|---|---|---|
| Code Engine | Free (100k req/mo) | Backend hosting | $0 within hackathon limits |
| Cloudant Lite | Free (1 GB) | All persistent state | $0 |
| watsonx.ai | $80 hackathon credits | Granite Code 8B inference | ~$0.0001 per 1K tokens |
| watsonx Orchestrate | hackathon-provisioned | Multi-agent orchestration | included |
| NLU Lite | Free (30k items/mo) | ABEND entity extraction | $0 |
| STT/TTS | Free (Lite tier) | Optional voice demo | $0 |

Full inventory in [`TOOLS_AND_SERVICES.md`](TOOLS_AND_SERVICES.md).

## Data flow — promote-job scenario

The single most important user flow. Maya promotes a JCL from int2 to int3.

```mermaid
sequenceDiagram
    actor Maya
    participant UI as Helios UI
    participant API as FastAPI
    participant Atlas as Region Atlas
    participant JJ as JJSCAN+
    participant Score as Confidence Score
    participant DB as Cloudant
    participant WX as watsonx.ai
    participant Review as Review Queue
    actor Raj

    Maya->>UI: Open CUST_DELETE_INACTIVE.JCL
    Maya->>UI: Click "Promote int2 → int3"
    UI->>API: POST /promote {jcl, source: int2, target: int3}
    API->>Atlas: load_region(int3)
    Atlas->>DB: GET region/int3
    DB-->>Atlas: region profile YAML
    Atlas->>API: substitution map (7 changes + reasons)
    API-->>UI: rewritten JCL + diff
    UI->>API: POST /scan (rewritten JCL)
    API->>JJ: scan(jcl)
    JJ->>WX: explain copybook drift in plain English
    WX-->>JJ: explanation
    JJ-->>API: findings list
    API->>Score: compute(findings, backup_status, history)
    Score->>DB: GET historical_abends for similar jobs
    DB-->>Score: ABEND stats
    Score-->>API: 62 (red) — top 3 reasons
    API-->>UI: gauge + reasons
    Maya->>UI: Accept auto-backup
    UI->>API: POST /generate_backup
    API->>Atlas: backup template for int3
    API-->>UI: paired UNLOAD + IMAGE COPY job
    Score-->>API: recompute → 94 (green)
    Maya->>UI: Apply copybook fix
    Score-->>API: recompute → 100 (green)
    Maya->>UI: Submit promotion for review
    UI->>Review: notify
    Review->>DB: write audit_log + queue entry
    DB-->>Review: change feed
    Review-->>Raj: WebSocket toast
    Raj->>UI: Approve
    UI->>API: POST /finalize
    API->>DB: append audit_log entry
```

## Deployment topology

```mermaid
flowchart LR
    subgraph dev[Developer Machines]
        BobG[Bob IDE - Golden]
        BobS[Bob IDE - Sayan]
        CCG[Claude Code - Golden silent]
    end

    subgraph github[GitHub]
        Repo[Helios repo<br/>main branch]
        Actions[GitHub Actions<br/>build + deploy]
        Pages[GitHub Pages<br/>Helios UI hosted here]
    end

    subgraph ibmcloud[IBM Cloud - us-south]
        CE[Code Engine<br/>FastAPI backend]
        CL[Cloudant Lite<br/>helios database]
        WXAI[watsonx.ai<br/>Granite Code endpoint]
        WXO[watsonx Orchestrate<br/>agent runtime]
    end

    BobG -.push.-> Repo
    BobS -.push.-> Repo
    CCG -.push.-> Repo
    Repo --> Actions
    Actions -->|deploy frontend| Pages
    Actions -->|deploy backend| CE
    Pages -.HTTPS.-> CE
    CE <--> CL
    CE <--> WXAI
    CE <--> WXO
```

## Security boundary

The trust boundary lives at the FastAPI gateway. Three classes of secret:

1. **In-browser** — none. The frontend is fully static; it talks to the backend over HTTPS and that's it.
2. **In Code Engine** — Cloudant credentials, watsonx API key, watsonx project ID. Stored as Code Engine secrets, mounted as env vars.
3. **On developer machines** — IBM Cloud API key, GitHub PAT, watsonx API key (for local Bob/Claude Code MCP servers). Stored in shell env vars only. Never in `.bob/mcp.json`, never in `.env` checked into the repo.

Full rules in [`SECURITY.md`](SECURITY.md).

## Why this architecture

A few non-obvious choices and their rationale:

**Static frontend on GitHub Pages.** Cheapest, fastest, zero ops. Backend can scale independently; frontend never goes down. Free tier covers anything the demo can throw at it.

**Cloudant over a SQL database.** Region profiles are heterogeneous (different shops will track different fields). JSON-native storage avoids the schema-migration treadmill. Cloudant's change feed is also what powers the real-time Review Queue with no extra infrastructure.

**Granite Code 8B, not 70B.** Smaller models are faster and cheaper, and Granite Code 8B is genuinely strong on COBOL — IBM trained it on the same corpora that power Watson Code Assistant for Z. Using a banned model would tank our judging score.

**Custom MCP servers in TypeScript.** Bob and Claude Code both speak MCP. Writing four small TS servers gives both clients identical access to Cloudant, watsonx, and the corpus. No duplicate glue code.

**No mainframe access.** We don't have a real LPAR. Trying to fake one would consume the entire hackathon. Instead we build a high-fidelity synthetic shop (MeridianBank) using GnuCOBOL test suite + opensourcecobol/Bankdemo as the COBOL source, run JCL through our parser without executing it, and stage SMF-shaped synthetic events for the anomaly demo. Judges who know mainframes will recognize the corpus quality immediately.
