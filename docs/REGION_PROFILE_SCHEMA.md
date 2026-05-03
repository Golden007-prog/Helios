# Region Profile Schema

The single most important data structure in Helios. Every region (`int1`, `int2`, `int3`, `dev1`, `dev2`, `dev3`, `prod`) is one of these YAML files.

Schema lives at `shared/schemas/region.json` (JSON Schema 2020-12). Validation runs on every read and write.

---

## Full example — `shared/sample-corpus/regions/int3.yaml`

```yaml
region: int3
description: "Integration test environment 3 — used for pre-prod release validation"
owner_team: "MERIDIAN_DEVOPS"
created: "2025-11-01T00:00:00Z"
last_modified: "2026-04-30T16:42:11Z"
last_modified_by: "golden"

hlq:
  application: "MERIDIAN.INT3"
  test_data: "MERIDIAN.INT3.TEST"
  backup: "MERIDIAN.INT3.BAK"
  archive: "MERIDIAN.INT3.ARCH"
  load: "MERIDIAN.INT3.LOAD"
  copylib: "MERIDIAN.INT3.COPYLIB"
  proclib: "MERIDIAN.INT3.PROCLIB"

steplib_concatenation:
  - "MERIDIAN.INT3.LOAD"
  - "MERIDIAN.SHARED.LOAD"
  - "SYS1.LINKLIB"

joblib_concatenation: []   # explicitly empty if not used

syslib_concatenation:
  - "MERIDIAN.INT3.COPYLIB"
  - "MERIDIAN.SHARED.COPYLIB"

db2:
  subsystem: "DBI3"
  collection: "MERIDIAN_INT3"
  default_plan: "MERIDPL3"
  default_qualifier: "MERINT3"
  bind_options:
    isolation: "CS"           # CS | RR | UR | RS
    acquire: "USE"            # USE | ALLOCATE
    release: "COMMIT"         # COMMIT | DEALLOCATE
    validate: "BIND"          # BIND | RUN
    explain: "YES"
    sqlerror: "NOPACKAGE"

racf:
  user_default: "MERINT3"
  groups:
    - "MERIDDEV"
    - "MERIDBATCH"
    - "MERIDDB2"
  resource_class_overrides: {}    # only set if region has custom RACF resource classes

jes:
  class: "C"
  msgclass: "X"
  notify: "MERIDOPS"

scheduler:
  queue: "INT3_BATCH"
  default_priority: 5

volser:
  primary: "INT3*"
  backup: "BAK3*"
  archive: "ARC3*"

jobcard_template: |
  //${JOBNAME} JOB (${ACCT}),'${PROGRAMMER}',
  //         CLASS=${jes.class},
  //         MSGCLASS=${jes.msgclass},
  //         NOTIFY=${jes.notify},
  //         REGION=0M,
  //         TIME=NOLIMIT

sysout_class: "X"
restart_strategy: "step"        # step | none | checkpoint

protected_resources:
  db2_tables:
    - "MERIDIAN.CUST_MASTER"
    - "MERIDIAN.ACCT_MASTER"
    - "MERIDIAN.TXN_HISTORY"
  vsam_clusters:
    - "MERIDIAN.INT3.CUSTPROC.KSDS"
  pds_libraries:
    - "MERIDIAN.INT3.LOAD"

backup_policy:
  retention_days: 30
  format_db2: "UNLOAD_PLUS_IMAGE_COPY"
  format_vsam: "IDCAMS_REPRO"
  dataset_pattern: "${hlq.backup}.${resource}.D${yyyyddd}.T${hhmmss}"

confidence_weights:
  severity:
    critical: 25
    high: 10
    medium: 5
    low: 2
  region_mismatch_per_resource: 15
  backup_gap: 30
  historical_abend_per_incident_30d: 5
  spec_match_bonus: 10

gating:
  green_threshold: 80
  amber_threshold: 60
override_required_role: "developer"   # in prod this becomes "tech_lead" or "release_manager"

aliases:
  - "i3"
  - "int_3"
  - "Integration3"

notes: |
  Migrated from int_3_legacy on 2026-01-15. DB2 subsystem upgraded
  from DBI3A to DBI3 in the same window. All BIND options retain
  legacy isolation level CS for backward compatibility with calling
  programs that assume cursor stability.
```

---

## Field-by-field reference

### Top-level identity

| Field | Type | Required | Notes |
|---|---|---|---|
| `region` | string | yes | Canonical region name. Must match filename (case-insensitive). Used as primary key in Cloudant. |
| `description` | string | yes | One-line human description. Surfaces in UI tooltips. |
| `owner_team` | string | yes | The team responsible. Could route ABEND notifications. |
| `created` | ISO 8601 | auto | Set on first write. |
| `last_modified` | ISO 8601 | auto | Updated on every save. |
| `last_modified_by` | string | auto | Helios username. |

### `hlq` — High-Level Qualifiers

Maps every dataset category to its HLQ prefix. The promote-job logic uses these to substitute dataset names. New shops add categories as needed (`scratch`, `sort_work`, etc.).

### `steplib_concatenation`, `joblib_concatenation`, `syslib_concatenation`

Lists in resolution order. JJSCAN+ walks these in this order when resolving PROC / COPYBOOK / member references. **Order matters** — first match wins.

### `db2`

Self-explanatory. The `bind_options` block controls everything `BIND PACKAGE` cares about. `db2_plan_mismatch` JJSCAN+ rule reads `collection` and `default_plan` to detect mismatches.

### `racf`

`user_default` — the RACF user the JOB statement runs under in this region. Can be overridden per-job.

`groups` — what groups this user belongs to. Used by Confidence Score to flag missing authorization risk when a job references a resource owned by a group the user isn't in.

### `jes`, `scheduler`, `volser`

Region-specific JES2/JES3 settings, scheduler queue, and VOLSER patterns. The volser patterns let us flag when a JCL hardcodes a volser that doesn't match the target region's pattern.

### `jobcard_template`

The promote-job logic regenerates the JOB card using this template, substituting variables like `${jes.class}`. This is what eliminates the most common manual edit during promotion.

### `protected_resources`

Critical. Lists the resources (DB2 tables, VSAM clusters, PDS libraries) that any destructive operation against MUST trigger a paired backup. Drives the auto-backup generator.

### `backup_policy`

How auto-backup is generated. `dataset_pattern` is a template with substitution variables:
- `${hlq.backup}` — resolves to `hlq.backup` from the same region
- `${resource}` — the resource name (with separators converted to dots)
- `${yyyyddd}` — Julian date
- `${hhmmss}` — time
- `${seq}` — sequence number for collisions

### `confidence_weights`

Per-region overrides for the Confidence Score formula. If absent, defaults from `shared/schemas/confidence_weights_default.yaml` are used. Production regions typically tighten these (critical = 50, backup_gap = 60).

### `gating`

Score thresholds for green / amber. Below `amber_threshold` is red. Production regions raise green_threshold to 90+.

### `override_required_role`

Who can override a red score. In dev/int regions it's any developer; in prod it's `tech_lead` or `release_manager`. Maps to a future RBAC layer (out of hackathon scope).

### `aliases`

Other names this region is known by. Lets users type `i3` instead of `int3`. Resolved at the API layer.

### `notes`

Free-text. Surfaces in the region YAML editor as a sidebar. Useful for "this region has a quirk" institutional knowledge.

---

## Validation

`shared/schemas/region.json` enforces:

- Required top-level fields present
- `region` matches `^[a-z][a-z0-9_]{1,32}$`
- `bind_options.isolation` ∈ {CS, RR, UR, RS}
- `bind_options.acquire` ∈ {USE, ALLOCATE}
- `bind_options.release` ∈ {COMMIT, DEALLOCATE}
- `confidence_weights` numbers all positive integers
- `gating.amber_threshold` < `gating.green_threshold`
- `restart_strategy` ∈ {step, none, checkpoint}

Validation runs on `PUT /regions/{name}` and on every region YAML edit in the Studio UI. Invalid YAML is rejected with structured error messages indicating the offending field path.

---

## Versioning

Each region profile in Cloudant carries an opaque `_rev` (CouchDB convention). When the YAML editor saves, it sends the `_rev` it loaded; if the doc has changed since (race condition), the save is rejected with a 409 and the user sees a "reload to see latest" prompt.

For human-readable history, the `audit_log` collection captures every save with a full diff. The Atlas UI exposes a "history" view per region: timeline of changes with diffs.

---

## How regions are seeded

`shared/sample-corpus/regions/` ships six MeridianBank regions: `dev1.yaml`, `dev2.yaml`, `dev3.yaml`, `int1.yaml`, `int2.yaml`, `int3.yaml`. Plus `prod.yaml` configured but with stricter weights and `override_required_role: "release_manager"`.

The seed script runs on backend startup if Cloudant `regions` collection is empty:

```python
# backend/scripts/seed_regions.py (pseudocode)
for yaml_file in glob("shared/sample-corpus/regions/*.yaml"):
    profile = yaml.safe_load(open(yaml_file))
    cloudant.put_doc("regions", profile["region"], profile)
```

For real-shop deployment, the seed step is replaced with import-from-file or import-from-mainframe-discovery (future).

---

## What's intentionally NOT in the schema

- Application-level secrets. Passwords, RACF tokens, key material. (Goes in IBM Cloud Secrets Manager or RACF KEYRING — not in YAML.)
- Per-job overrides. The schema models a region; per-job snowflakes go in a sibling `overrides/` collection (Phase 2 feature).
- Audit history. Lives in a separate Cloudant database (`audit_log`).

---

## Future schema extensions (post-hackathon)

- `cics` block for CICS resource definitions, transaction codes, RDO references
- `ims` block for PSB/DBD references, transaction codes
- `mq` block for queue manager IDs and queue name patterns
- `kafka` block (yes, mainframes ship Kafka now via Event Streams for z/OS) for connector configurations
- `tags` for arbitrary key-value labels (cost center, environment color, etc.)
