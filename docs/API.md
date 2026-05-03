# API Reference — Helios Backend

The Helios backend exposes a JSON HTTP API plus one WebSocket. This document is the contract between backend (Golden) and frontend (Sayan). Any change to the API requires updating this file in the same PR.

Base URL (local): `http://localhost:8080`
Base URL (deployed): `https://helios-backend.<hash>.us-south.codeengine.appdomain.cloud`

OpenAPI live spec: `GET /openapi.json` (FastAPI auto-generates).
Swagger UI: `GET /docs` (development only).

## Authentication

All endpoints except `/healthz` and `/openapi.json` require a bearer JWT.

```http
Authorization: Bearer <jwt>
```

Tokens are issued by `POST /auth/login` (development bootstraps from seeded users; production hooks SSO — see `docs/ROADMAP.md`).

## Response envelope

Every successful response:

```json
{
  "ok": true,
  "data": { ... },
  "request_id": "req:01HXY..."
}
```

Every error:

```json
{
  "ok": false,
  "error": {
    "code": "REGION_NOT_FOUND",
    "message": "No region named 'int7' in shop 'meridianbank'.",
    "details": {}
  },
  "request_id": "req:01HXY..."
}
```

`request_id` appears in every backend log line for that request. Frontend should surface it on errors so users can tell support exactly which request failed.

## Rate limits

- 100 req/min per user for read endpoints
- 30 req/min per user for write endpoints
- Burst of 20

Exceeded → `429 Too Many Requests` with `Retry-After` header.

---

## Catalog

| Group | Path prefix | Doc section |
|---|---|---|
| Health | `/healthz`, `/readyz` | §1 |
| Auth | `/auth/...` | §2 |
| Regions | `/api/regions/...` | §3 |
| JCL artifacts | `/api/jcl/...` | §4 |
| Promote | `/api/promote/...` | §5 |
| JJSCAN+ | `/api/scan/...` | §6 |
| Confidence Score | `/api/score/...` | §7 |
| ABEND | `/api/abend/...` | §8 |
| Runbooks | `/api/runbooks/...` | §9 |
| Audit log | `/api/audit/...` | §10 |
| Learning | `/api/learning/...` | §11 |
| Review Queue | `/api/queue/...` | §12 |
| WebSocket | `/ws/queue` | §13 |

---

## §1 — Health

### `GET /healthz`
Liveness probe. Returns `200 {"ok":true}` if the process is up.

### `GET /readyz`
Readiness probe. Returns `200 {"ok":true}` only if Cloudant is reachable AND watsonx.ai is reachable. `503` otherwise with `data.failed_dependencies[]`.

## §2 — Auth

### `POST /auth/login`
Body: `{ "email": "...", "password": "..." }`
Returns: `{ "token": "...", "expires_at": "...", "user": {...} }`

For the hackathon, accepts seeded MeridianBank users (`maya`, `anil`, `raj`) with password `helios2026`. Production SSO is a Phase 2 item.

### `POST /auth/logout`
Invalidates the current session. Returns `204`.

### `GET /auth/me`
Returns the current user document.

## §3 — Regions

### `GET /api/regions`
List all regions. Supports `?tier=integration|production`.

### `GET /api/regions/{name}`
Full region profile.

### `POST /api/regions/{name}` (write)
Create or update a region. Body: full `RegionProfile` (see `docs/REGION_PROFILE_SCHEMA.md`). Writes audit event `region_profile_edit` and may enqueue a Review Queue item per region policy.

### `GET /api/regions/{a}/diff/{b}`
Side-by-side diff of two regions.
Returns: `{ "fields": [{ "path": "db2.subsystem_id", "a": "DBI2", "b": "DBI3", "kind": "value_change" }, ...] }`

### `POST /api/regions/{name}/forks/{job_name}`
Create a job-specific override layer on top of region defaults. Body: `{ "overrides": { "db2.subsystem_id": "DBI2X", ... }, "reason": "..." }`. The fork is itself a JSON document under `helios_regions` with `kind: "region_override"`.

## §4 — JCL artifacts

### `GET /api/jcl?region={r}`
List artifacts in a region. `?state=promoted|draft|archived`, `?score_lt=80` etc.

### `GET /api/jcl/{region}/{name}`
Full artifact document including current score and breakdown.

### `GET /api/jcl/{region}/{name}/source`
Returns the raw JCL text. `Content-Type: text/plain`.

### `POST /api/jcl/{region}/{name}` (write)
Create or replace JCL source. Body: `{ "source": "...", "reason": "..." }`. Writes audit event.

### `GET /api/jcl/{region}/{name}/history`
Audit history for this artifact (delegates to `/api/audit?subject=...`).

## §5 — Promote

### `POST /api/promote`
The hero endpoint. Body:

```json
{
  "jcl_name": "CUST_DELETE_INACTIVE.JCL",
  "source_region": "int2",
  "target_region": "int3",
  "auto_apply_fixes": ["generate_paired_backup", "update_syslib"]
}
```

Returns:

```json
{
  "promote_event_id": "evt:...",
  "diff": [{...}],
  "confidence_score": 100,
  "confidence_breakdown": {...},
  "auto_fixes_applied": [{...}],
  "auto_fixes_available_but_not_applied": [],
  "state": "approved" | "pending_review" | "rejected",
  "reviewer": "anil@meridianbank.demo" | null
}
```

If the resulting score meets the region's `auto_approve_threshold` AND no protected resources are in play, the promote is `approved` immediately. Otherwise it enters the Review Queue and `state=pending_review`.

### `GET /api/promote/{event_id}`
Status of a promote.

### `POST /api/promote/{event_id}/cancel`
Cancel a pending-review promote. Initiator only.

## §6 — JJSCAN+

### `POST /api/scan`
Body: `{ "jcl_source": "...", "target_region": "int3" }` OR `{ "jcl_name": "...", "region": "int3" }`.
Returns:

```json
{
  "findings": [
    {
      "id": "find:...",
      "rule_id": "JJ-COPYBOOK-DRIFT-001",
      "severity": "medium",
      "description": "...",
      "details": {...},
      "auto_fix_available": true,
      "dissent_count": 7,
      "dissent_total": 9,
      "common_dismiss_reasons": ["semantic_equivalent", "report_only"]
    }
  ],
  "scan_duration_ms": 142
}
```

### `POST /api/scan/findings/{id}/decide`
Body: `{ "decision": "accept" | "dismiss", "reason": "...", "reason_tags": [...] }`. Writes audit event AND learning event.

### `POST /api/scan/findings/{id}/auto-fix`
Apply the auto-fix if available. Returns the updated artifact and new score.

## §7 — Confidence Score

### `POST /api/score`
Compute a score for a candidate JCL without persisting.
Body: `{ "jcl_source": "...", "region": "int3" }` returns `{ "score": 94, "breakdown": {...} }`.

### `GET /api/score/weights/{region}`
Current weights for a region (defaults + overrides merged).

### `POST /api/score/weights/{region}` (write)
Update weights. Body: `{ "weights": {...}, "reason": "..." }`. Always Review Queue-gated for production-tier regions.

### `POST /api/score/{event_id}/override`
Override a recorded score. Body: `{ "new_score": 88, "reason": "..." }`. Writes audit + learning events.

## §8 — ABEND

### `POST /api/abend`
The ABEND Archaeologist entry point. Body:

```json
{
  "raw_text": "<paste of SYSLOG / JESYSMSG / CEEDUMP>",
  "context": {
    "region": "prod",
    "job_name": "CUST_DELETE_INACTIVE",
    "occurred_at": "2026-11-12T03:14:08Z"
  }
}
```

Returns:

```json
{
  "identified_abend": {
    "code": "S0C7",
    "message_id": "IGZ0035S",
    "confidence": 0.97
  },
  "failing_step": {
    "step_name": "STEP020",
    "program": "CUSTPROC",
    "offset_hex": "0x1A4"
  },
  "source_trace": {
    "file": "shared/sample-corpus/MERIDIANBANK/cobol/CUSTPROC.cbl",
    "line": 247,
    "paragraph": "2300-CALC-RETIREMENT",
    "highlighted_field": "WS-CUST-DOB-INT"
  },
  "business_rule_explanation": "...",      // Granite Code generated
  "ranked_root_causes": [
    { "cause": "null DOB row", "prior_count": 13, "confidence": 0.91 },
    { "cause": "...", "...": "..." }
  ],
  "matching_runbooks": [
    { "id": "runbook:S0C7-CUSTPROC-age-calc:01HXY...", "title": "...", "success_count": 12 }
  ]
}
```

### `POST /api/abend/{event_id}/resolve`
Body: `{ "root_cause_choice": "null_dob_row", "applied_runbook_id": "...", "outcome": "resolved" | "did_not_resolve" }`. Writes learning events to refine ABEND priors.

## §9 — Runbooks

### `GET /api/runbooks?abend_code=S0C7&program=CUSTPROC`
Top-K runbooks for a context, ranked by `success_count`.

### `GET /api/runbooks/{id}`
Full runbook document.

### `POST /api/runbooks` (write)
Create new runbook (usually invoked by the ABEND resolution flow, occasionally manually).

### `POST /api/runbooks/{id}/apply`
Marks an application attempt; outcome filled in by `POST /api/runbooks/{id}/outcome` later.

## §10 — Audit log

### `GET /api/audit`
Query with any combination:
- `subject_kind`, `subject_name`, `subject_region`
- `actor`
- `type`
- `from`, `to` (ISO 8601)
- `format=json|csv|ndjson` (default json)
- `cursor`, `limit` (pagination; max limit 200)

Returns events oldest-first within the result page.

### `GET /api/audit/{event_id}`
Single event.

### `POST /api/audit/bundle`
Body: query params identical to GET /api/audit. Returns a `tar.gz` containing matching events, referenced before/after blobs, daily attestations, and `MANIFEST.json`. Async job — returns `{ "bundle_job_id": "..." }`; poll `GET /api/audit/bundle/{job_id}`.

### `GET /api/audit/attestation/{date}`
The chain root hash for that day. `date` in `YYYY-MM-DD`.

## §11 — Learning

### `GET /api/learning/dissent`
`?rule_id=...&region=...` returns `{ "dissent_count": 7, "dissent_total": 9, "common_reasons": [...] }`. Used by JJSCAN+ frontend.

### `GET /api/learning/abend-priors`
`?abend_code=S0C7&program=CUSTPROC` returns ranked root-cause priors.

### `GET /api/learning/runbook-rank`
`?abend_code=S0C7&program=CUSTPROC` returns ranked runbooks.

## §12 — Review Queue

### `GET /api/queue`
List pending reviews visible to the current user. `?state=pending_review|approved|rejected|all`.

### `POST /api/queue/{event_id}/approve`
Body: `{ "reason": "..." }`. Reviewer cannot be the initiator. Writes audit update; triggers downstream effect (e.g., the actual JCL write).

### `POST /api/queue/{event_id}/reject`
Body: `{ "reason": "..." }`.

### `GET /api/queue/since?seq={seq}`
Polling fallback when the WebSocket is unavailable. Returns events newer than `seq`.

## §13 — WebSocket

### `wss://<base>/ws/queue?token=<jwt>`

Server pushes one JSON message per relevant audit event:

```json
{
  "type": "audit_event",
  "seq": 14223,
  "event": { /* full event document */ }
}
```

Client filters which events to render based on user role and current page.

Heartbeat: server sends `{"type":"ping"}` every 25 s. Client replies `{"type":"pong"}`. Connections idle for 60 s without a pong are dropped; client reconnects with exponential backoff (initial 1 s, max 30 s, jitter ±20%).

On reconnect, client calls `GET /api/queue/since?seq=<lastSeq>` to backfill missed events.

---

## Errors — codes catalog

| Code | HTTP | Meaning |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid bearer token |
| `FORBIDDEN` | 403 | Authenticated but lacking role |
| `REGION_NOT_FOUND` | 404 | Named region does not exist in shop |
| `JCL_NOT_FOUND` | 404 | Named JCL not in target region |
| `RULE_NOT_FOUND` | 404 | Unknown JJSCAN+ rule id |
| `RUNBOOK_NOT_FOUND` | 404 | Unknown runbook |
| `EVENT_NOT_FOUND` | 404 | Unknown audit event |
| `INVALID_PAYLOAD` | 422 | Body schema validation failed; details include offending field path |
| `REVIEW_REQUIRED` | 409 | Action requires review and was not auto-approved |
| `SELF_REVIEW_FORBIDDEN` | 409 | Initiator cannot approve their own request |
| `STATE_TRANSITION_INVALID` | 409 | Cannot transition from current state to requested state |
| `RATE_LIMITED` | 429 | Throttled; see Retry-After |
| `WATSONX_UPSTREAM` | 502 | Granite call failed; details include upstream message |
| `CLOUDANT_UPSTREAM` | 502 | Cloudant call failed |
| `INTERNAL` | 500 | Unhandled; check `request_id` in logs |

## Example: Maya's promote — wire trace

```http
POST /api/promote HTTP/1.1
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "jcl_name": "CUST_DELETE_INACTIVE.JCL",
  "source_region": "int2",
  "target_region": "int3",
  "auto_apply_fixes": ["generate_paired_backup", "update_syslib"]
}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ok": true,
  "data": {
    "promote_event_id": "evt:2026-10-23T16:12:03.114Z:promote:01HXY7QJ...",
    "diff": [...7 entries...],
    "confidence_score": 100,
    "confidence_breakdown": {...},
    "auto_fixes_applied": [{"fix":"generate_paired_backup","target":"CUST.INT3.BKP.D26296.T161203"}, {"fix":"update_syslib","from":"v2.7","to":"v3.1"}],
    "state": "pending_review",
    "reviewer": null
  },
  "request_id": "req:01HXY7QK..."
}
```

Then over the WebSocket on Anil's side:

```json
{
  "type": "audit_event",
  "seq": 14223,
  "event": { /* the same event document */ }
}
```

## Changelog policy

Every endpoint addition, removal, or breaking change is recorded in `CHANGELOG.md` under the API section AND in this file's git history. Frontend should pin to a backend version via the `X-Helios-API-Version: 1` header (current value: `1`); breaking changes bump that integer.
