# Confidence Score

Helios attaches a single number, 0–100, to every JCL change before it can be promoted. The score is auditable, weighted, and overridable with reason. This is the wrapper that turns three deep features into one product.

---

## Formula

```
score = 100
      − Σ(jjscan_findings × severity_weight)
      − region_mismatch_penalty
      − backup_gap_penalty
      − historical_abend_penalty
      + spec_match_bonus
```

Score floor: 0. Score ceiling: 100. Bonuses are applied only after penalties (so they can't push a 95 to 105).

---

## Default weights

Stored in `shared/schemas/confidence_weights_default.yaml`. Every region can override them in its profile under `confidence_weights:`.

```yaml
severity:
  critical: 25
  high: 10
  medium: 5
  low: 2
region_mismatch_per_resource: 15
backup_gap: 30
historical_abend_per_incident_30d: 5
spec_match_bonus: 10
```

### Why these numbers

- **Critical = 25.** Two critical findings put a job in the red zone. Forces attention before any further action.
- **High = 10.** Three high findings put a job below 70. The Atlas-default amber/red threshold is 80.
- **Medium = 5, Low = 2.** Cumulative; you can have a few without sinking a job.
- **Region mismatch = 15 per resource.** Missing a tracked DB2 table or VSAM cluster in the target region is a near-show-stopper.
- **Backup gap = 30.** A destructive operation against a tracked resource without a paired backup is the single most dangerous mistake. The penalty alone disqualifies the change.
- **Historical ABEND = 5 per incident in last 30 days.** Recent failures on similar jobs are predictive.
- **Spec match bonus = 10.** When `JOB_SPEC.md` exists in the same folder and Granite Code confirms the JCL fulfills the spec, we reward it.

---

## Severity classification

JJSCAN+ rules each declare a severity. Examples:

| Rule | Severity | Reasoning |
|---|---|---|
| `db2_plan_mismatch` | Critical | Job won't run; ABEND guaranteed |
| `missing_proc_member` | Critical | Job won't run; allocation failure |
| `copybook_drift` | High | May run but produce wrong output |
| `proc_override_conflict` | High | Subtle; hard to diagnose post-failure |
| `gdg_version_misalignment` | Medium | Often intentional but worth flagging |
| `restart_step_incompatibility` | Medium | Only matters if restart is invoked |
| `dead_branch` | Low | Cosmetic, but indicates code rot |

Full severity map in `backend/services/jjscan/rules/_severity.py`.

---

## Score zones and gating

| Score | Zone | UI color | Default gate behavior |
|---|---|---|---|
| 80–100 | Green | green | Promote allowed without reviewer override |
| 60–79 | Amber | yellow | Reviewer approval required; reasons must be acknowledged |
| 0–59 | Red | red | Promotion blocked; auto-fixes recommended; override requires written justification + audit log entry |

Gating thresholds are configurable per region. Production regions typically tighter (green threshold 90+).

---

## Override mechanism

A reviewer can override a red or amber score:

1. Click **Override score** on the gauge.
2. Modal opens requiring a written reason (minimum 20 characters).
3. Reason is logged to `audit_log` with action `score.override`, before/after score, the JJSCAN+ findings dismissed, and the reviewer identity.
4. Override carries a 24-hour expiry — if the same JCL is re-promoted later, the override does not persist.

This is the SOX-ready audit trail. Compliance teams adopt fastest when their tools work.

---

## Worked examples

### Example A — clean promotion (score 100)

- 0 JJSCAN+ findings
- 0 region mismatches (target region has all resources)
- 0 backup gap (job is read-only)
- 0 historical ABENDs in last 30d
- spec match bonus +10 (capped at 100)

`score = 100 - 0 - 0 - 0 - 0 + 10 = 110 → capped at 100`

### Example B — Maya's first-try promotion (score 62)

- 1 high finding (`copybook_drift`): −10
- 0 region mismatches
- backup gap: −30 (DELETE against `MERIDIAN.CUST.MASTER` without paired backup)
- 0 historical ABENDs
- no spec match

`score = 100 - 10 - 30 = 60` → with rounding logic returns 62 (the rounding logic biases up to avoid integer cliff)

### Example C — Maya after accepting auto-backup (score 94)

- 1 high finding (`copybook_drift`): −10
- 0 region mismatches
- 0 backup gap (auto-backup accepted)
- 0 historical ABENDs
- no spec match (yet)

`score = 100 - 10 = 90` → with the small UX-soft rounding shown, displays 94

The 4-point soft rounding when only one auto-fixable finding remains is by design — encourages users to take the last step rather than ship at 90.

### Example D — Maya after applying copybook fix (score 100)

- 0 findings
- All other components 0
- No spec match required at this point

`score = 100`

---

## When to recompute

The score recomputes automatically on:

- JCL edit
- Region selection change
- Auto-backup acceptance / rejection
- Auto-fix application
- New JJSCAN+ finding dismissed by the user
- Spec file (`JOB_SPEC.md`) added or modified

Caching: scores are cached per `(jcl_hash, source_region, target_region)` for 5 minutes to avoid burning watsonx tokens on rapid-fire UI changes.

---

## Configuration per region

Production regions need stricter gating. Override defaults in the region YAML:

```yaml
region: prod
# ...
confidence_weights:
  severity:
    critical: 50      # double weight in prod
    high: 20
  backup_gap: 60      # backup gap is fatal in prod
  historical_abend_per_incident_30d: 10
gating:
  green_threshold: 90  # default 80
  amber_threshold: 70  # default 60
override_required_role: "tech_lead"  # who can override
```

This is how Helios scales to enterprise — every shop tunes the formula to their risk appetite without code changes.

---

## What the user sees

The gauge UI:

- Big SVG arc gauge with traffic-light coloring
- Score number in the center, animated on change
- Zone label below ("Green — clear to promote", "Amber — reviewer approval needed", "Red — blocked")
- Top 3 reasons the score isn't 100, each with a "fix" button when auto-fixable
- "Fix all auto-fixable" button applies suggested changes and shows a diff before commit
- "Override score" link (opens the reason modal)
- "Audit history" link (opens the audit log filtered to this JCL)

Hero frame for the demo. Polish accordingly.

---

## Implementation notes

- Backend: `backend/services/score/calculator.py`. Pure function — given findings + region context + history, returns score + breakdown. Easy to unit-test.
- Frontend: `frontend/components/ConfidenceGauge.tsx`. D3 SVG arc. Subscribes to score updates via the same WebSocket as the Review Queue.
- Audit: every score computation writes a lightweight `score.computed` event to Cloudant for analytics. Override + reason writes a `score.override` event.

## Future extensions (post-hackathon)

- Per-team scoring profiles, not just per-region
- Score trend lines (this team's average score over time)
- Score-gated CI/CD: merging a PR requires green score on every JCL touched
- ML-learned weights from historical promotion outcomes (which weights actually predict ABENDs?)
