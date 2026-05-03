# Learning Loop — How Helios Learns Your Shop's Dialect

## Purpose

Every mainframe shop is different. The same JJSCAN+ rule that catches a real bug at one bank produces noise at another. The same ABEND root cause that takes Maya 4 minutes can take a different team 4 hours because their codebase has a different convention.

The Learning Loop is Helios's mechanism for adapting to the specific shop it runs in. Every accepted finding, every dismissed false positive, every Confidence Score override, every confirmed-or-disputed ABEND root cause is captured as a labeled signal in the `helios_learning` collection. Subsequent Helios runs use those signals to surface the right warnings to the right people at the right confidence threshold.

The pitch line: **"Helios learns the dialect of your shop."**

## Scope — what feedback is captured

| Source | Signal | Stored as |
|---|---|---|
| JJSCAN+ finding accepted | "true positive" | `feedback_jjscan_accept` |
| JJSCAN+ finding dismissed with reason | "false positive in this context" | `feedback_jjscan_dismiss` |
| Confidence Score override (raise) | "score model too pessimistic here" | `feedback_score_raise` |
| Confidence Score override (lower) | "score model too optimistic here" | `feedback_score_lower` |
| ABEND root cause confirmed by reviewer | "Helios got it right" | `feedback_abend_confirm` |
| ABEND root cause disputed | "Helios got it wrong, actual cause was X" | `feedback_abend_dispute` |
| Runbook applied successfully | "this runbook worked" | `feedback_runbook_success` |
| Runbook applied but did not resolve | "runbook needs update" | `feedback_runbook_fail` |
| Promoted JCL ran successfully in target region | "score+substitutions were correct" | `feedback_promotion_success` |
| Promoted JCL ABENDed in target region within 24h | "score missed something" | `feedback_promotion_failure` |

The last two are particularly powerful because they are gathered automatically — Helios subscribes to the JES2 SMF feed (or its synthetic stand-in for the demo) and matches new ABENDs against recent promotions.

## Document schema (`helios_learning`)

```json
{
  "_id": "lrn:<iso8601_ts>:<source>:<ulid>",
  "schema_version": "1.0",
  "source": "feedback_jjscan_dismiss",
  "ts": "2026-10-23T16:18:42.301Z",
  "actor": "maya@meridianbank.demo",
  "actor_role": "developer",

  "rule_id": "JJ-COPYBOOK-DRIFT-001",
  "subject": {
    "kind": "jcl",
    "name": "EOD_REPORT.JCL",
    "region": "int2",
    "shop": "meridianbank"
  },

  "context_features": {
    "jcl_class": "report_generator",
    "touches_db2": false,
    "touches_vsam": true,
    "uses_proc_chain": ["DBLOAD", "REPORT"],
    "copybook_resolved_to": "REPORTREC v1.4",
    "copybook_drift_distance": "minor",
    "region_class": "integration"
  },

  "decision": "dismiss",
  "decision_reason_text": "Report-only job, copybook drift between v1.4 and v1.5 is field-rename only, no semantic change.",
  "decision_reason_tags": ["semantic_equivalent", "report_only"],
  "decision_confidence": 0.95,

  "outcome_observed_at": null,
  "outcome": null
}
```

Outcomes are filled in later by the SMF watcher when the job actually runs. If the dismissed-as-false-positive job ABENDs within 24h with a related symptom, `outcome` becomes `false_negative_dismiss` and the model learns this dismissal was wrong.

## How the learning is used

### 1. Surface dissent at the moment of decision

When JJSCAN+ produces a finding, the UI now shows:

```
┌──────────────────────────────────────────────────────────────┐
│ ⚠ Copybook drift — REPORTREC v1.4 vs v1.5                   │
│   Severity: medium                                            │
│                                                                │
│   ℹ Your shop dismissed this rule on similar jobs 7 of 9     │
│     times in the last 30 days. Common reason:                 │
│     "field-rename only, no semantic change."                  │
│                                                                │
│   [ Accept ] [ Dismiss ] [ Always dismiss for this jobclass ] │
└──────────────────────────────────────────────────────────────┘
```

This is the killer UX moment. The developer sees not just the rule, but how their team has historically reacted to it. They can dismiss with one click, or they can investigate further if the prior dismissal reasons don't match their current situation.

### 2. Adjust default Confidence Score weights per region

Once the shop has 30+ feedback signals on a given rule in a given region, the per-region weight is auto-tuned. If `JJ-COPYBOOK-DRIFT-001` is dismissed as false-positive 80% of the time in `int2`, its severity weight in `int2` drops from `medium=5` to `low=2`. The change is recorded as a `feedback_weight_autotune` event in the audit log so it is fully traceable.

This is gated by an explicit feature flag (`enable_weight_autotune`) and a minimum sample size (`autotune_min_samples = 30`). For the hackathon demo, the flag is on, samples are seeded.

### 3. Suggest dismissal reasons

When dismissing a finding, the reason field auto-completes with the top dismissal reasons your team has used previously for that rule. This both speeds dismissal and standardizes the language, which makes the data more useful for future learning.

### 4. ABEND root cause priors

When ABEND Archaeologist parses a new SYSLOG, it consults:

- The pre-seeded ABEND pattern library (`docs/ABEND_PATTERN_LIBRARY.md`) — universal patterns
- The shop's `feedback_abend_confirm` and `feedback_abend_dispute` signals — local refinements

If your shop has 15 prior `S0C7` events in `CUSTPROC` and 13 of them were caused by null DOB rows (the seeded scenario), the next `S0C7` in `CUSTPROC` ranks "null DOB" as the top hypothesis even before the SYSLOG is fully analyzed. This is what makes the demo feel uncannily fast.

### 5. Runbook ranking

The Runbook Generator already produces entries. The Learning Loop ranks them: a runbook with 12 successful applications and 0 failures is shown above one with 2 successes and 1 failure for the same ABEND class.

## Implementation — keep it boring

This is not a training pipeline. It is **labeled retrieval** with a tiny adjustment layer on top:

- Cloudant index on `(shop, rule_id, region, subject.kind)` for the dissent-surfacing query.
- Cloudant index on `(shop, abend_code, affected_program)` for ABEND priors.
- Per-region weight overrides stored in `helios_regions/<region>/confidence_weights` and recomputed nightly by `backend/jobs/learning_autotune.py`.
- All "model output" is presented as suggestions with the underlying counts visible. No black box.

We do not train embeddings. We do not fine-tune Granite. We do not run an MLOps pipeline. The whole loop is queryable in plain Cloudant Mango.

That boringness is a feature. A judge from a regulated bank wants to know they can reason about every output Helios produces. "We do `SELECT count(*) FROM dismissals WHERE rule = X AND shop = Y` and surface the result" is a sentence that wins trust in 5 seconds.

## Bootstrapping — what the fresh corpus looks like

The MeridianBank corpus ships with seeded learning data so the demo shows the loop working:

| Seed | Count | Purpose |
|---|---|---|
| `JJ-COPYBOOK-DRIFT-001` dismissals on report jobs in int2 | 7 | Power the dissent example above |
| `S0C7` confirmations on CUSTPROC null-DOB cause | 13 | Power ABEND priors in Scene 2 |
| Runbook `S0C7_CUSTPROC_age_calc` successes | 12 | Top-rank in runbook list |
| Promote successes for CUST_DELETE_INACTIVE int1→int2 | 6 | Show "high confidence in similar promotions" |

Seed file: `shared/sample-corpus/MERIDIANBANK/learning_seed.json`. Loaded by `_seed.sh` via `tools/load_learning_seed.py`.

## Privacy and shop-data leakage

The `helios_learning` collection is scoped per shop. Helios will never use one customer's signals to influence another customer's recommendations. The `shop` field on every document enforces this at the query layer.

For the hackathon demo, only one shop exists (MeridianBank). The architecture supports multi-tenant from day one because we knew judges would ask.

## What we are NOT doing for the hackathon

- Active learning loop that retrains a classifier (overkill, demos badly)
- Cross-shop federated learning (post-hackathon Phase 3 conversation)
- Negative learning from external CVE feeds (Phase 2)
- Embedding similarity for "rules that behave like this rule" (Phase 2)
- Learning loop dashboard with per-rule precision/recall (Phase 2 — interesting but won't fit demo)

## The Q&A line

When a judge asks "how does Helios get smarter?", the answer is:

> Every accept, dismiss, override, and outcome is captured with full context in a Cloudant collection. We surface the team's historical decisions inline at the moment of new decisions, and we auto-tune per-region severity weights once we have enough signal. It is fully auditable, fully reversible, and presented as suggestions — never as fait accompli. Boring infrastructure, big behavior change.

## Implementation pointers

| Concern | File | Owner |
|---|---|---|
| Feedback writer | `backend/services/learning_writer.py` | Golden |
| Dissent query for UI | `backend/api/learning.py::get_dissent` | Golden |
| ABEND prior query | `backend/api/learning.py::get_abend_priors` | Golden |
| Weight autotune nightly job | `backend/jobs/learning_autotune.py` | Golden |
| SMF watcher (synthetic for demo) | `backend/jobs/smf_outcome_watcher.py` | Golden |
| Dissent UI on findings panel | `frontend/components/FindingDissent.tsx` | Sayan |
| Reason autocomplete | `frontend/components/DismissalReason.tsx` | Sayan |
| Demo seed loader | `tools/load_learning_seed.py` | Either |
