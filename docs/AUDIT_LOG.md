# Audit Log — SOX-Ready Provenance Trail

## Purpose

Every state-changing action in Helios writes an immutable record to the `helios_audit_log` collection in Cloudant. The audit log is queryable, exportable, and tamper-evident. This is the artifact that lets a regulated bank adopt Helios on day one without their compliance officer blocking the rollout.

The pitch line: **"SOX-ready audit trail, day one."**

## Scope — what is logged

Every operation that mutates Helios state OR mutates an external system (a PDS member, a DB2 catalog row, a region profile) writes an event. Read-only operations do not write events.

| Category | Examples | Required fields beyond base |
|---|---|---|
| Region profile | edit, create, delete, fork-as-job-override | `region_name`, `field_diffs[]` |
| JCL promotion | promote, rollback | `jcl_name`, `source_region`, `target_region`, `confidence_score`, `auto_fixes[]` |
| JJSCAN+ findings | accept, dismiss, bulk-dismiss | `finding_id`, `rule_id`, `decision_reason` |
| Confidence Score | override, weights edit | `original_score`, `new_score`, `override_reason` |
| Backup generator | run, suppress | `backup_dataset_name`, `protected_resource` |
| ABEND triage | resolve, dispute_root_cause | `abend_code`, `affected_program`, `runbook_id` |
| Runbook | create, edit, delete, retire | `runbook_id`, `applies_to[]` |
| Review Queue | request, approve, reject, auto-approve | (covered in REVIEW_QUEUE.md schema) |
| Auth | login, logout, role_change | `auth_method`, `previous_roles`, `new_roles` |
| MCP server | enable, disable, config_change | `server_name`, `command`, `args_hash` |

## Base event schema

Every event document has these fields:

```json
{
  "_id": "evt:<iso8601_ts>:<type>:<ulid>",
  "schema_version": "1.0",
  "type": "<see categories above>",
  "actor": "<email or service principal>",
  "actor_role": "<developer|team_lead|admin|service>",
  "ts": "<iso8601 with millisecond precision>",
  "ts_unix_ms": 1729715523114,
  "subject": { "kind": "<jcl|region|finding|...>", "name": "<...>", "...": "..." },
  "before_sha256": "<hex of canonicalized before-state>",
  "after_sha256":  "<hex of canonicalized after-state>",
  "before_blob_ref": "<optional, for full payload retrieval>",
  "after_blob_ref":  "<optional>",
  "result": "<success|failed|cancelled>",
  "error": "<present only if result=failed>",
  "client_meta": {
    "user_agent": "<string>",
    "ip_hash": "<sha256(ip + daily_salt)>",
    "session_id": "<ulid>"
  },
  "chain": {
    "prev_event_id": "<id of previous event in this chain, or null>",
    "prev_event_hash": "<sha256 of prev event canonical form, or null>",
    "this_event_hash": "<sha256 of this event canonical form>"
  }
}
```

The `chain` field implements **hash chaining**: each event's hash is computed over its own canonical form plus the previous event's hash. Tampering with any historical event breaks the chain at every subsequent event, which is detectable by re-validating from the chain root.

## Tamper-evidence — practical guarantees

The audit log is not blockchain — we are not asking judges to trust a Merkle proof. What it does guarantee:

1. **No in-place edits.** Cloudant document updates create a new revision; the prior revision remains in the database. The Helios backend writes events with `_id` derived from content + timestamp, so duplicate writes are no-ops, not overwrites.
2. **Hash chain detects tampering.** A nightly job (`backend/jobs/audit_chain_verify.py`) walks the entire chain and writes a daily attestation document with the chain root hash. If anyone edits a historical event in Cloudant via direct admin access, the next nightly run flags the break.
3. **Daily attestation is exportable.** `GET /api/audit/attestation/<date>` returns the chain root hash for that day. A bank can store these externally (e.g., emailed to the compliance officer's archive) so even a full Cloudant compromise cannot rewrite history without detection.

This is enough for a SOX/SOC2/HIPAA conversation. It is not enough for cryptocurrency-grade proofs, and we do not claim it is.

## Canonicalization

Hashes are computed over the **canonical JSON** form of each event (RFC 8785 / JCS):

- Keys sorted lexicographically.
- No insignificant whitespace.
- UTF-8 encoded.
- The `chain.this_event_hash` field excluded from the input to the hash function.

Implemented in `backend/services/audit_canonical.py`. Test vectors live in `backend/tests/audit_canonical_test_vectors.json`.

## Querying

The audit log supports four query patterns out of the box:

### 1. By artifact

```http
GET /api/audit?subject_kind=jcl&subject_name=CUST_DELETE_INACTIVE.JCL
```

Returns every event touching that JCL, oldest-first. Backed by Cloudant index on `subject.kind, subject.name, ts_unix_ms`.

### 2. By actor

```http
GET /api/audit?actor=maya@meridianbank.demo&since=2026-10-01
```

### 3. By region

```http
GET /api/audit?subject_region=int3&type=region_profile_edit
```

### 4. By time window

```http
GET /api/audit?from=2026-10-23T00:00:00Z&to=2026-10-23T23:59:59Z
```

All endpoints support `format=json|csv|ndjson` for export.

## The "auditor question" demo

In the demo or Q&A, expect: *"Can you show me who changed the int3 BIND parameters between October 14 and November 2?"*

Live, on the Helios UI:

1. Open Audit tab.
2. Filter: subject_kind=region, subject_name=int3, type=region_profile_edit, time window Oct 14 – Nov 2.
3. Three rows appear. Click the most recent. Side-by-side YAML diff shows the BIND parameter changed from `ACTION(REPLACE) RETAIN(YES)` to `ACTION(REPLACE) RETAIN(NO)`. Reviewer was Anil. Reason recorded was *"reduce orphaned packages in int3 staging."*
4. Total elapsed: under 30 seconds.

Today, that same question takes Maya half a day across Endevor, Slack, and Confluence. Helios answers it in 30 seconds. Make sure the demo includes this moment — it is the single most powerful audit story.

## Retention

| Data class | Retention | Storage |
|---|---|---|
| Event documents | 7 years (SOX-compliant) | Cloudant primary |
| Blob refs (full before/after payloads) | 7 years | Cloudant attachments OR object storage if large |
| Daily attestation | 7 years | Cloudant + email export |
| `client_meta.ip_hash` salt | 24 hours | Backend memory + nightly rotated S3 archive |

For the hackathon demo, retention is set to *forever* on the demo Cloudant — we are not running cleanup jobs.

## Privacy

The audit log records *who did what to which mainframe artifact*. It does not record personal data of bank customers (we never read row content from `CUST.MASTER` into events; only schema-level diffs). The `actor` field is an email or service principal; no other PII is captured.

The IP hash uses a daily-rotated salt so the same IP appearing on two different days produces different hashes — this is a deliberate accommodation between auditability and the right-to-be-forgotten.

## Export formats

Auditors want CSV. Investigators want NDJSON. Helios devs want JSON. All three are supported via `?format=`. The CSV export flattens the `subject`, `chain`, and `client_meta` nested objects with dotted keys (`subject.name`, `chain.prev_event_id`, etc.).

There is also a one-shot **bundle export**: `POST /api/audit/bundle` produces a tar.gz containing the matching events, all referenced before/after blobs, the daily attestations covering the time window, and a `MANIFEST.json` with chain validation status. This is the artifact you hand to an outside auditor.

## What we are NOT doing for the hackathon

- Active write-ahead-log to a separate cloud (Phase 3 — would protect against full Cloudant compromise)
- Customer-managed encryption keys for blob storage (Phase 2)
- Cryptographic signing of events with per-actor keys (Phase 3 — current model trusts the backend)
- SIEM forwarding (Phase 2 — straightforward to add via webhook fan-out)

## Implementation pointers

| Concern | File | Owner |
|---|---|---|
| Event writer | `backend/services/audit_writer.py` | Golden |
| Canonicalization | `backend/services/audit_canonical.py` | Golden |
| Hash-chain verifier | `backend/jobs/audit_chain_verify.py` | Golden |
| Query endpoints | `backend/api/audit.py` | Golden |
| Export bundle builder | `backend/services/audit_bundle.py` | Golden |
| Audit UI tab | `frontend/components/AuditTab.tsx` | Sayan |
| Daily attestation email job | `backend/jobs/audit_attestation_email.py` | Golden (post-hackathon) |

The audit_writer is a hard dependency for Phase 2 of `docs/PHASE_PLAN.md` — every state-changing endpoint must call it. Add a backend lint rule (`tools/lint_audit_calls.py`) that scans for endpoints decorated `@state_changing` and verifies they call `audit_writer.write_event` somewhere in the call tree.

## One sentence to remember

> *Every change Helios makes is logged with who, when, why, the full before/after, the active Confidence Score, and a tamper-evident hash chain. The audit log is itself queryable through Helios. SOX-ready, day one.*
