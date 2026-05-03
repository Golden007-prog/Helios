# Audit Writer — Implementation Notes

Notes on how the audit writer landed vs `docs/audit_writer_plan.md`. Bob should read this before doing the review pass + Phase 1.5 export.

## Schema choice — Helios shape, Bob's algorithm

Bob's plan §2 proposes a flat envelope (`prev_event_hash`, `event_hash`, `actor_id`, `payload`, `ip_hash`, etc.). The Helios docs (`docs/AUDIT_LOG.md` §"Base event schema", `docs/API.md` §10) define a **nested-chain** envelope:

```jsonc
{ "_id": "evt:<ts>:<type>:<ulid>", "kind": "audit_event", "type": "...",
  "actor": "...", "actor_role": "...", "ts": "...", "ts_unix_ms": 0,
  "subject": { "kind": "...", "name": "..." },
  "before_sha256": "...", "after_sha256": "...",
  "result": "...", "client_meta": { "ip_hash": "...", "user_agent": "...", "session_id": "..." },
  "chain": { "prev_event_id": "...", "prev_event_hash": "...", "this_event_hash": "..." } }
```

The shipped writer keeps the **Helios shape** (matches every API endpoint and every doc) and applies **Bob's algorithm** (RFC 8785 canonicalization in `app.utils.canonical_json`, GENESIS marker for the first event, deterministic hash chain).

Bob: if you'd prefer the flat shape, re-spec `docs/AUDIT_LOG.md` and `docs/API.md` first — the writer is the easy part to swap once those settle.

## Filesystem layout

Bob's plan said `backend/services/audit_writer.py` etc. The repo lays out as `backend/app/services/...`. Final placement:

| Bob's plan path | Shipped path |
|---|---|
| `backend/utils/canonical_json.py` | `backend/app/utils/canonical_json.py` |
| `backend/models/audit_event.py` | `backend/app/models/audit.py` (existing — schemas merged) |
| `backend/services/audit_writer.py` | `backend/app/services/audit_writer.py` |
| `backend/migrations/cloudant_indexes.json` | `backend/migrations/cloudant_indexes.json` (rewritten — see PART B notes below) |
| `backend/tests/audit_canonical_test_vectors.json` | same |
| `backend/tests/test_audit_writer.py` | same |
| `backend/tests/test_audit_chain.py` | same |
| `backend/tests/test_audit_tampering.py` | same |
| `backend/tests/test_canonical_json.py` | same |

## Test vector hashes — all real

Bob's plan §6 left the `expected_sha256` values as `"8f3e4d…"` placeholders. The shipped vectors carry **real** SHA-256 hashes computed from the exact `input` objects with `app.utils.canonical_json.canonicalize`. If the canonicalization algorithm changes, regenerate via:

```python
import hashlib
from app.utils.canonical_json import canonicalize_bytes
hashlib.sha256(canonicalize_bytes(vector_input)).hexdigest()
```

## What's NOT in this writer (intentional)

- **`ip_hash` is in `client_meta`, not a top-level field.** Matches `docs/AUDIT_LOG.md`. Callers that have a request IP pass it through `client_meta`; the writer doesn't capture HTTP request state itself (FastAPI middleware would be a cleaner injection point — open question for Bob).
- **No `user_agent_hash` field on the audit event.** Helios stores the raw user-agent string in `client_meta.user_agent` per the existing schema. Hashing it is a Phase 2 privacy ratchet.
- **No `session_id` discrimination.** Sessions are stateless JWTs in the demo; `client_meta.session_id` is a hook for when we add server-side sessions.
- **Frozen Pydantic model not yet added.** Bob's plan §2 wanted Pydantic v2 `frozen=True`. The current `AuditEvent` model in `backend/app/models/audit.py` is mutable to keep the existing query path simple. If you want frozen semantics, switch the model and the audit query response together.

## Lint enforcement

`tools/lint_audit_calls.py` walks every `backend/app/api/*.py` route, identifies state-changing decorators (POST/PUT/DELETE/PATCH), and asserts each reaches a `write_event` call. Pre-commit hook `lint-audit-calls` is wired in `.pre-commit-config.yaml`.

Allowlist semantics: routes that are read-only or stateless (logout 204, health probes) are explicitly listed in `ALLOWLIST` in the lint script with comments explaining why.

## Wired endpoints

Endpoints that already wrote audit events before this pass:
- `POST /api/regions/{name}` (region_atlas upsert)
- `POST /api/regions/{name}/forks/{job}`
- `POST /api/scan/findings/{id}/decide`
- `POST /api/score/weights/{region}`
- `POST /api/score/{event_id}/override`
- `POST /api/abend/{event_id}/resolve`
- `POST /api/queue/{event_id}/approve` and `/reject` (via the `_decide` helper)

Newly wired in this pass:
- `POST /auth/login` — emits `auth.login` (success) or `auth.login_failed` (failure).
- `POST /auth/logout` — emits `auth.logout`.

Not wired (Bob territory):
- `POST /api/promote` — Bob's hero endpoint; will write the audit event when the diff/score/auto-fix pipeline lands.
- `POST /api/scan/findings/{id}/auto-fix` — also Bob.

## Test suite — 33 tests across 4 files

| File | Count | Coverage |
|---|---|---|
| `test_canonical_json.py` | 11 | RFC 8785 vectors, key ordering, whitespace, Unicode, NaN rejection, recursion, list-order preservation |
| `test_audit_writer.py` | 8 | GENESIS marker, chain linkage, deterministic event_id format, secret redaction, timestamp precision, ULID uniqueness |
| `test_audit_chain.py` | 7 | Integrity across 10/100 events, GENESIS marker, cross-instance tip persistence, concurrent writes |
| `test_audit_tampering.py` | 7 | Modified payload/timestamp/actor, broken link, inserted/deleted/reordered events |

All 33 pass on the in-memory Cloudant fallback (no network required).

## Open questions for Bob's review pass

1. Should the writer accept a `request: Request` parameter so FastAPI middleware injects `client_meta.ip_hash` automatically, instead of leaving it to each caller?
2. Daily attestation export — is the format in `docs/AUDIT_LOG.md` §"Export formats" still right?
3. The `chain.prev_event_hash` index in `cloudant_indexes.json` is wide; the chain-verifier job rarely uses it on the hot path. Drop?
