# Testing — Demo Day Validation

Demos fail when something untested breaks live. This document is the validation regime that catches every category of failure before the judge ever sees a screen.

Three test levels:

1. **Unit / integration** — runs in CI on every PR
2. **Demo smoke** — runs locally before every rehearsal AND the morning of the demo
3. **Resilience** — runs once before final dress rehearsal; verifies the failure mitigations in `docs/DEMO_SCRIPT.md` actually work

---

## §1 — CI: unit and integration

### Backend

```bash
cd backend
pytest -q
```

Coverage targets (enforced in CI):

| Layer | Target |
|---|---|
| `services/` | 85% |
| `api/` | 80% |
| `jobs/` | 70% |
| `migrations/` | covered indirectly by integration |

Critical paths with golden tests (pytest fixtures locked to bytewise output):

- `services/audit_canonical.py::canonicalize` — RFC 8785 vectors in `tests/audit_canonical_test_vectors.json`
- `services/audit_writer.py::write_event` — chain hash continuity
- `services/score.py::compute` — every example in `docs/CONFIDENCE_SCORE.md` Worked Examples A–D
- `services/region_atlas.py::diff` — every region pair in the corpus
- `services/jjscan/rules/*` — golden findings for each of the 4 demoed rules

### Frontend

```bash
cd frontend
npm test
```

- Component tests for `<DiffViewer>`, `<ReviewQueue>`, `<ConfidenceGauge>`, `<FindingDissent>`.
- Playwright e2e tests for the three demo flows (promote, scan, abend).

### Integration (cross-stack)

Spun up via `docker-compose up` in `tests/integration/`. Hits real local Cloudant (CouchDB), mocks watsonx.ai. Verifies:

- Round-trip promote → audit event → review queue notification arrives at WebSocket subscriber within 1 s.
- Audit chain validates after 100 sequential events.
- Cloudant `_changes` feed survives reconnect after 5-second network drop.

CI fails the PR if any test category drops below threshold.

## §2 — Demo smoke — the 8-step round-trip

Run this before every rehearsal AND on the morning of the demo. If any step fails, the demo is not ready.

```bash
make demo-smoke
```

Which runs:

```bash
#!/usr/bin/env bash
set -euo pipefail
echo "1. Health"
curl -fsS http://localhost:8080/healthz | jq -e '.ok == true' >/dev/null
echo "2. Ready"
curl -fsS http://localhost:8080/readyz  | jq -e '.ok == true' >/dev/null
echo "3. Login as Maya"
TOKEN=$(curl -fsS -X POST localhost:8080/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"maya@meridianbank.demo","password":"helios2026"}' | jq -r .data.token)
H="Authorization: Bearer $TOKEN"
echo "4. Region diff int2 vs int3"
curl -fsS -H "$H" localhost:8080/api/regions/int2/diff/int3 | jq -e '.data.fields | length == 7' >/dev/null
echo "5. Promote (no auto-fixes)"
EID=$(curl -fsS -X POST -H "$H" -H 'Content-Type: application/json' localhost:8080/api/promote \
  -d '{"jcl_name":"CUST_DELETE_INACTIVE.JCL","source_region":"int2","target_region":"int3","auto_apply_fixes":[]}' \
  | jq -r .data.promote_event_id)
echo "   event id: $EID"
echo "6. Score arrived"
SCORE=$(curl -fsS -H "$H" localhost:8080/api/promote/$EID | jq .data.confidence_score)
test "$SCORE" -eq 62 || { echo "expected 62, got $SCORE"; exit 1; }
echo "7. Apply auto-fixes; expect 100"
curl -fsS -X POST -H "$H" -H 'Content-Type: application/json' localhost:8080/api/promote \
  -d '{"jcl_name":"CUST_DELETE_INACTIVE.JCL","source_region":"int2","target_region":"int3","auto_apply_fixes":["generate_paired_backup","update_syslib"]}' \
  | jq -e '.data.confidence_score == 100' >/dev/null
echo "8. Audit log shows two events for this artifact"
COUNT=$(curl -fsS -H "$H" "localhost:8080/api/audit?subject_kind=jcl&subject_name=CUST_DELETE_INACTIVE.JCL" | jq '.data | length')
test "$COUNT" -ge 2 || { echo "expected ≥2 events, got $COUNT"; exit 1; }
echo "ALL GREEN"
```

Total runtime: ~6 seconds. Exit code 0 = ready.

## §3 — ABEND smoke

Separate because it touches Granite Code:

```bash
make abend-smoke
```

```bash
#!/usr/bin/env bash
set -euo pipefail
TOKEN=...   # as above
H="Authorization: Bearer $TOKEN"
RAW=$(cat tests/fixtures/syslog_s0c7_custproc.txt)
RESP=$(curl -fsS -X POST -H "$H" -H 'Content-Type: application/json' localhost:8080/api/abend \
  -d "$(jq -n --arg raw "$RAW" '{raw_text:$raw, context:{region:"prod", job_name:"CUST_DELETE_INACTIVE", occurred_at:"2026-11-12T03:14:08Z"}}')")
echo "$RESP" | jq -e '.data.identified_abend.code == "S0C7"' >/dev/null
echo "$RESP" | jq -e '.data.failing_step.program == "CUSTPROC"' >/dev/null
echo "$RESP" | jq -e '.data.source_trace.line == 247' >/dev/null
echo "$RESP" | jq -e '.data.ranked_root_causes[0].cause | contains("null DOB")' >/dev/null
echo "$RESP" | jq -e '.data.matching_runbooks[0].title | length > 0' >/dev/null
echo "ABEND SMOKE GREEN"
```

If watsonx.ai is unreachable, the `business_rule_explanation` may be empty, but `identified_abend`, `failing_step`, `source_trace`, `ranked_root_causes`, and `matching_runbooks` come from local logic and the Cloudant-backed pattern library. The demo can survive a watsonx outage with a tasteful "explanation generator temporarily unavailable" line — the rest still works.

## §4 — Resilience — fail the things on purpose

Run once before final dress rehearsal. Each scenario simulates a known-possible demo-day failure.

### S1 — Internet drops mid-demo

```bash
sudo pfctl -e -f tests/resilience/block_outbound.pf
make abend-smoke   # should fail gracefully — backend returns degraded mode
sudo pfctl -d
```

Expected: `POST /api/abend` returns `200` with all fields except `business_rule_explanation`, plus `data.degraded: true` and `data.degraded_reason: "watsonx_unreachable_using_cached_priors"`. UI shows a non-scary banner: *"AI explanation temporarily unavailable. Cached analysis below."*

### S2 — Cloudant rate-limit (Lite tier hits 20 RPS)

Run a stress harness that issues 50 concurrent reads:

```bash
ab -n 200 -c 50 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/regions/int3
```

Expected: backend retries with exponential backoff, no requests fail with 5xx, P95 latency ≤ 800 ms. If P95 > 800 ms in CI, fail the build and tighten the cache layer.

### S3 — WebSocket dies

Mid-promote, kill the WebSocket process:

```bash
kill $(pgrep -f ws_queue.py)
# observe frontend reconnect with backoff
# observe POST /api/queue/since polling fallback kicks in
```

Expected: reviewer notification arrives within 3 s via polling (degraded from <1 s WebSocket). UI shows a small "polling mode" indicator in the corner — visible to the dev, invisible to a casual viewer.

### S4 — Bob IDE goes dark

Demo backup plan: run the same flow from a terminal using `httpie` while narrating. The point is the product, not the IDE; the IDE is a delivery mechanism.

```bash
http :8080/api/promote @demo_payload.json "Authorization:Bearer $TOKEN"
```

### S5 — One developer's laptop dies

Spare a USB drive with the entire repo + a `.env.spare` checked into the team's password vault (NOT git). Either of you can be on either laptop within 5 minutes.

### S6 — Wi-Fi at venue is broken

Tether from a phone. Pre-tested before traveling. Backup tether SIM acquired and tested.

If all six scenarios pass, demo confidence is high.

## §5 — Performance budgets

Hard ceilings — exceeding any during smoke = block the demo:

| Endpoint | P50 | P95 |
|---|---|---|
| `GET /api/regions` | 50 ms | 200 ms |
| `GET /api/regions/{a}/diff/{b}` | 80 ms | 250 ms |
| `POST /api/promote` (no auto-fixes) | 350 ms | 1.2 s |
| `POST /api/promote` (with auto-fixes) | 600 ms | 1.8 s |
| `POST /api/scan` | 200 ms | 600 ms |
| `POST /api/abend` | 1.2 s | 3 s |
| WebSocket end-to-end propagation | 200 ms | 800 ms |

Anything slower than P95 reads as "not real" to the judge. Optimize before the demo.

## §6 — The judge trick — the audit query

In Q&A judges sometimes ask: *"Show me everything Maya did today."* This is a real-time ad-hoc query, not a rehearsed demo step. Practice it.

```
Audit tab → filter actor=maya@meridianbank.demo, today → results in <1s
```

If this answer takes more than 2 s, the demo loses its punch. Ensure the index `(shop, actor, ts_unix_ms)` is present and used (`EXPLAIN` plan reviewed in CI).

## §7 — Pre-demo checklist (printed on paper, taped above the keyboard)

```
□ make demo-smoke           # 8 steps, all green
□ make abend-smoke          # 5 assertions, all green
□ Bob IDE open, all 4 MCP green dots
□ Frontend tab: localhost:3000, logged in as Maya
□ Frontend tab #2: incognito, logged in as Anil (for review demo)
□ Browser DevTools closed (no red console errors visible)
□ Phone tethered, tested
□ Slack notifications muted on demo machine
□ macOS notifications: Do Not Disturb ON
□ Screen recording started (in case of redo request)
□ Audit query muscle memory: rehearsed 3× in last 2 hours
□ Water on table, not next to laptop
```

Tape this list to the demo desk. The goal is zero in-flight thinking about anything except the story.

## §8 — Post-demo

Within an hour of finishing:

```bash
# Capture the state of the system at demo completion
make demo-snapshot
```

Which writes `bench/snapshots/<timestamp>/` containing:

- A Cloudant export of every collection
- The final state of the audit log
- The screen recording
- The Bob session export

Useful for write-ups, judge follow-ups, and the inevitable "show me again" requests.
