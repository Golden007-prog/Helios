# Data Model — Cloudant Collections

Helios persists state in IBM Cloudant (Lite tier). This document is the single source of truth for every collection's schema, indexes, and access patterns. If a backend service needs to read or write Cloudant, it must conform to what is here.

## Why Cloudant Lite

- **Free tier sufficient for the demo** — 1 GB storage, 20 RPS reads, 10 RPS writes. The MeridianBank corpus + Helios state fits in under 100 MB.
- **HTTP API** — every backend service calls it the same way; no native driver headaches.
- **`_changes` feed** — the foundation of the Review Queue's real-time delivery and the Learning Loop's outcome watcher.
- **Document-oriented** — JCL, region profiles, and audit events have wildly different shapes; rigid schemas would be fought against, not used.

## Collection inventory

| Collection | Purpose | Detail doc |
|---|---|---|
| `helios_regions` | Region profiles + per-region overrides | `docs/REGION_PROFILE_SCHEMA.md` |
| `helios_audit_log` | Tamper-evident change history | `docs/AUDIT_LOG.md` |
| `helios_learning` | Feedback signals for the Learning Loop | `docs/LEARNING_LOOP.md` |
| `helios_abend_patterns` | Pre-seeded ABEND root-cause patterns | `docs/ABEND_PATTERN_LIBRARY.md` |
| `helios_runbooks` | Generated runbook entries | This doc, §5 |
| `helios_jcl_artifacts` | JCL state — original + promoted variants + scores | This doc, §6 |
| `helios_findings` | Open + historical JJSCAN+ findings | This doc, §7 |
| `helios_users` | Identity, roles, preferences | This doc, §8 |
| `helios_sessions` | Active session tokens (short-lived) | This doc, §9 |

## §1 — Naming conventions

- Collection names: `helios_<plural_noun>`, snake_case, underscored.
- Document `_id`: `<kind>:<sortable_key>:<ulid>` so range-scans by kind and time are cheap. Examples: `evt:2026-10-23T16:12:03Z:promote:01HXY...`, `region:int3:01HXY...`, `lrn:2026-10-23T16:18:42Z:feedback_jjscan_dismiss:01HXY...`.
- ULID for the unique tail (lexicographically time-sortable, no GUID dashes).
- Field names: snake_case JSON.
- Timestamps: ISO 8601 with millisecond precision in `ts`, plus a parallel `ts_unix_ms` integer field for index efficiency.
- Hashes: lowercase hex SHA-256.

## §2 — Common envelope

Every document carries:

```json
{
  "_id": "...",
  "_rev": "...",                  // managed by Cloudant
  "schema_version": "1.0",
  "kind": "<collection-specific>",
  "ts": "2026-10-23T16:12:03.114Z",
  "ts_unix_ms": 1729715523114,
  "shop": "meridianbank"          // multi-tenant scope, even though demo has only one shop
}
```

The `shop` field on every document means we can multi-tenant from day one without schema migration. For the hackathon, every document gets `"shop": "meridianbank"`.

## §3 — `helios_regions`

Full schema in `docs/REGION_PROFILE_SCHEMA.md`. Summary:

```json
{
  "_id": "region:int3:01HXY...",
  "kind": "region",
  "name": "int3",
  "tier": "integration",
  "hlq": "CUST.INT3",
  "db2": {
    "subsystem_id": "DBI3",
    "plan_collection": "CUSTPKG.INT3",
    "default_bind": { "action": "REPLACE", "retain": "YES", "isolation": "CS" }
  },
  "racf_group": "INT3DEV",
  "jes": { "class": "P", "sysout_class": "S" },
  "scheduler_queue": "BATCH_INT",
  "volser_pattern": "INT3*",
  "gdg_retention": 30,
  "protected_resources": ["CUST.MASTER"],
  "confidence_weight_overrides": {
    "critical": 37,    // 25 × 1.5 (strict region)
    "high": 15
  },
  "review": {
    "auto_approve_threshold": 90,
    "allowed_reviewers": { ... }
  }
}
```

Indexes:

- `(shop, name)` — unique
- `(shop, tier)` — list regions by environment class

## §4 — `helios_audit_log`

Full schema and discussion in `docs/AUDIT_LOG.md`. Indexes:

- `(shop, subject.kind, subject.name, ts_unix_ms)` — audit by artifact (the demo query)
- `(shop, actor, ts_unix_ms)` — audit by actor
- `(shop, type, ts_unix_ms)` — audit by event type
- `(shop, state)` partial index for `state=pending_review` — powers the Review Queue's change feed

The Cloudant `_changes` feed with `filter=audit_log/pending_review` is the substrate for the Review Queue.

## §5 — `helios_runbooks`

Generated runbook entries. Each entry is a markdown body plus structured metadata:

```json
{
  "_id": "runbook:S0C7-CUSTPROC-age-calc:01HXY...",
  "kind": "runbook",
  "title": "S0C7 in CUSTPROC age calculation",
  "applies_to": [
    { "abend_code": "S0C7", "program": "CUSTPROC", "paragraph": "2300-CALC-RETIREMENT" },
    { "abend_code": "IGZ0035S", "program": "CUSTPROC" }
  ],
  "body_markdown": "# Symptom\n\n...\n\n# Likely cause\n\n...\n\n# Fix\n\n...",
  "fix_actions": [
    {
      "label": "Quarantine bad rows",
      "type": "sql",
      "language": "sql",
      "code": "UPDATE CUST.MASTER SET STATUS = 'QUARANTINE' WHERE DOB IS NULL;"
    }
  ],
  "created_by": "system|<actor>",
  "created_from_event_id": "evt:...",
  "success_count": 12,
  "failure_count": 0,
  "last_applied_at": "2026-10-29T14:08:11Z"
}
```

Indexes:

- `(shop, applies_to.abend_code, applies_to.program)` — top-K runbook lookup by ABEND class
- `(shop, success_count)` — global runbook ranking

## §6 — `helios_jcl_artifacts`

Tracks every distinct JCL we have seen plus its variants across regions:

```json
{
  "_id": "jcl:CUST_DELETE_INACTIVE:int3:01HXY...",
  "kind": "jcl_artifact",
  "name": "CUST_DELETE_INACTIVE.JCL",
  "region": "int3",
  "state": "promoted",
  "source_blob_sha256": "c1b7...",
  "source_blob_ref": "blob:int3/CUST_DELETE_INACTIVE.JCL@c1b7...",
  "promoted_from": {
    "region": "int2",
    "blob_sha256": "a3f9...",
    "promote_event_id": "evt:..."
  },
  "current_confidence_score": 100,
  "current_confidence_breakdown": { ... },
  "open_findings_count": 0,
  "last_modified_event_id": "evt:..."
}
```

Indexes:

- `(shop, name, region)` — find an artifact by name + environment
- `(shop, region, current_confidence_score)` — list low-score JCLs in a region for triage

## §7 — `helios_findings`

JJSCAN+ findings — open, accepted, dismissed:

```json
{
  "_id": "find:JJ-COPYBOOK-DRIFT-001:int3:CUST_DELETE_INACTIVE:01HXY...",
  "kind": "finding",
  "rule_id": "JJ-COPYBOOK-DRIFT-001",
  "severity": "medium",
  "subject": { "kind": "jcl", "name": "CUST_DELETE_INACTIVE.JCL", "region": "int3" },
  "description": "Copybook CUSTREC resolves to v3.1 in source; SYSLIB chain in int3 currently pins v2.7.",
  "details": {
    "copybook": "CUSTREC",
    "source_version": "v3.1",
    "target_resolves_to": "v2.7",
    "syslib_chain": ["CUST.INT3.COPYLIB", "CUST.SHARED.COPYLIB"]
  },
  "state": "open",            // open | accepted | dismissed | superseded
  "decided_at": null,
  "decided_by": null,
  "decision_reason": null,
  "auto_fix_available": true,
  "auto_fix_applied_at": null
}
```

Indexes:

- `(shop, subject.region, state, severity)` — backlog of open findings by region
- `(shop, rule_id, state)` — feeds the Learning Loop's dissent counts

## §8 — `helios_users`

Minimal identity + role + preferences. For the hackathon demo we have four seeded users (Maya, Anil, Raj, plus a service principal):

```json
{
  "_id": "user:maya@meridianbank.demo:01HXY...",
  "kind": "user",
  "email": "maya@meridianbank.demo",
  "display_name": "Maya Patel",
  "roles": ["developer"],
  "preferences": {
    "default_region_view": "int2",
    "show_dissent_inline": true,
    "notify_on_review_decision": true
  },
  "created_at": "2026-10-01T00:00:00Z",
  "last_login_at": "2026-10-23T15:54:08Z"
}
```

Indexes:

- `(shop, email)` — unique
- `(shop, roles[])` — list reviewers

For the hackathon we do not implement full SSO; sessions are bootstrapped from a seeded JWT signed with `JWT_SECRET`. Production-readiness pointer in `docs/ROADMAP.md`.

## §9 — `helios_sessions`

Short-lived session records (TTL 24 h via Cloudant `_design/sessions/_purge`):

```json
{
  "_id": "sess:01HXY...",
  "kind": "session",
  "user_id": "user:maya@meridianbank.demo:01HXY...",
  "issued_at": "2026-10-23T15:54:08Z",
  "expires_at": "2026-10-24T15:54:08Z",
  "ip_hash": "sha256:..."
}
```

Indexes:

- `(shop, user_id)` — list active sessions for a user
- `(shop, expires_at)` — cleanup scan

## §10 — Cross-collection invariants

These are checked nightly by `backend/jobs/data_invariants_check.py`:

| Invariant | If violated |
|---|---|
| Every `state=accepted` finding has at least one `feedback_jjscan_accept` learning event | Backfill or warn |
| Every `state=approved` audit event has a corresponding state mutation in the relevant artifact collection | Investigate; possible orphan |
| Every `helios_jcl_artifacts.last_modified_event_id` resolves to a real audit event | Repair pointer |
| Every `helios_runbooks.success_count` matches `count(feedback_runbook_success)` | Recompute |
| `helios_audit_log.chain.this_event_hash` of event N+1's `chain.prev_event_hash` matches event N's `chain.this_event_hash` | Tamper alert (see `docs/AUDIT_LOG.md`) |

## §11 — Indexes — practical Cloudant Mango syntax

Example index creation (idempotent — Cloudant is OK if it already exists):

```http
POST /helios_audit_log/_index
Content-Type: application/json

{
  "index": { "fields": ["shop", "subject.kind", "subject.name", "ts_unix_ms"] },
  "name": "by-shop-kind-name-time",
  "type": "json"
}
```

All indexes are declared in `backend/migrations/cloudant_indexes.json` and applied by `backend/migrations/apply_indexes.py` on every deploy.

## §12 — Backups

Cloudant Lite does not provide automated backups. Mitigation:

- Nightly `cloudant-dump` job runs in Code Engine, exports every collection to a tar.gz, uploads to IBM Cloud Object Storage (Lite tier — also free).
- 30-day rolling retention.
- Restore tested weekly.

For the hackathon demo, a manual export is captured the morning of the demo and stored locally — even total Cloudant loss does not prevent the demo from running.

## §13 — Migration policy

Schema versions are tracked per document via the `schema_version` field. Migrations are forward-only. A migration script lives in `backend/migrations/<NNN>_description.py` and updates documents in batches with the new version. Old code paths are removed only after every document of that kind has been migrated.

The hackathon ships at `schema_version: "1.0"` for everything. Migrations are infrastructure, not features.

## §14 — Why not Postgres / why not a vector store

- **Postgres** would force a schema for documents whose shape (audit events especially) varies meaningfully. We would either over-normalize or stuff everything into JSONB columns and lose Postgres's ergonomics.
- **Vector store** is unnecessary for this product. The Learning Loop is labeled retrieval, not embedding similarity. ABEND pattern matching is regex + structured priors, not semantic search. If we add semantic features in Phase 3 (e.g., "find runbooks similar to this incident"), a vector store becomes a useful adjunct — not a replacement for Cloudant.

## §15 — One-line summary

Cloudant Lite, document-oriented, multi-tenant from day one via a `shop` field on every document, hash-chained audit log, change-feed-powered real-time UI, all indexes declared in version-controlled JSON. Boring, predictable, fits in the free tier through demo day.
