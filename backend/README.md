# Helios Backend

FastAPI service that fronts Cloudant and watsonx.ai for the Helios control plane.
Owns the four feature pillars (Region Atlas, JJSCAN+, ABEND Archaeologist,
Confidence Score), the audit log, the Review Queue, and the Learning Loop.

## Layout

```
backend/
  app/
    api/          HTTP routes — one module per feature group in docs/API.md
    services/    Business logic (Cloudant, watsonx, audit writer, region engine, …)
    jobs/        Background work (queue interface + in-memory & Cloudant impls)
    models/      Pydantic request/response schemas (mirrored in shared/python)
    middleware.py Request-id + structured logging
    errors.py    Error envelope + catalogue (mirrors docs/API.md § Errors)
    config.py    Settings via pydantic-settings (.env)
    main.py      FastAPI factory
  migrations/    Cloudant index DDL + idempotent seed scripts
  mcp/           Custom Helios MCP servers (cloudant, ibm-cloud, corpus, watsonx)
  tests/         Pytest suite mirroring app/
  Dockerfile     Code Engine target image
```

## Local dev

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows; on POSIX, .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8080
```

Swagger UI: <http://localhost:8080/docs> · OpenAPI: <http://localhost:8080/openapi.json>

## Configuration

All settings come from environment variables, normally loaded from `.env` at
the repo root (see `.env.example`). Required for full readiness:

| Var | Purpose |
|---|---|
| `CLOUDANT_URL`, `CLOUDANT_APIKEY` | Cloudant Lite — backing store |
| `WATSONX_URL`, `WATSONX_PROJECT_ID`, `WATSONX_APIKEY` | watsonx.ai (Granite Code 8B) |
| `JWT_SECRET` | HS256 signing key for session JWTs |
| `IBM_CLOUD_REGION` | Defaults to `us-south` |
| `CORS_ORIGINS` | Comma-separated allow-list. Defaults to the GH Pages origin |

## Tests

```bash
pytest                 # unit + integration
pytest -m "not e2e"    # skip the live e2e
pytest --cov=app       # coverage
```

Stubbed feature endpoints have contract tests that assert they return `501`
with a `BOB:` marker in `error.message` — when Bob fills them in, the contract
test is the first thing that flips green.

## What's a stub vs what's real

| Layer | State |
|---|---|
| Routing, validation, auth, audit calls, error envelope | Real |
| Cloudant + watsonx clients, retry, banned-model guard | Real |
| Background job queue interface + in-memory impl | Real |
| Region Atlas diff algorithm | Stub — `BOB:` |
| JJSCAN+ rule scanners | Stub — `BOB:` |
| ABEND inference pipeline | Stub — `BOB:` |
| Confidence Score formula | Stub — `BOB:` |
| Cloudant-backed job queue impl | Stub — `BOB:` |

Run `python -m app.tools.list_bob_stubs` to print the full Bob worklist.
