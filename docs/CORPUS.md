# MeridianBank Synthetic Corpus

The demo corpus for Helios. This is the fake-but-realistic mainframe shop that every screenshot, every demo, and every metric in the README is run against.

## Why a synthetic shop

Real mainframe customer code cannot be shown in a hackathon demo without an NDA. Public COBOL corpora are either toy snippets (one program, no realism) or buried in 1990s archives. So we assemble our own from open-source, MIT/Apache-licensed COBOL projects, rename the headers to `MERIDIANBANK`, and stitch them together with synthetic JCL, DB2 DDL, and copybooks.

The result is large enough to demo dependency graphs, varied enough to demo Region Atlas substitutions, and broken enough in known places to demo JJSCAN+ and ABEND Archaeologist.

## Source ingredients

| Source | License | Used for |
|---|---|---|
| [GnuCOBOL test suite](https://sourceforge.net/projects/gnucobol/) | GPL-3 (test data only) | Programs exercising COBOL syntax variety |
| [opensourcecobol/Bankdemo](https://github.com/opensourcecobol/Bankdemo) | Apache-2.0 | Account, customer, transaction structures |
| [NIST COBOL85 conformance suite](https://www.itl.nist.gov/div897/ctg/cobol_form.htm) | Public domain | Edge-case constructs for JJSCAN+ rules |
| Hand-authored | Helios MIT | JCL, DB2 DDL, region profiles, broken-on-purpose variants |

We do not redistribute the ingredients themselves. The corpus repo references them via download script (`shared/sample-corpus/_seed.sh`) and applies a patch overlay that does the renaming and stitching. This keeps Helios's repo clean and licensing tidy.

## Layout

```
shared/sample-corpus/MERIDIANBANK/
├── cobol/
│   ├── CUSTPROC.cbl          ← customer master driver, ~1200 lines, contains the seeded S0C7
│   ├── ACCTOPEN.cbl          ← account opening flow
│   ├── ACCTCLOSE.cbl         ← account closing + dormant detection
│   ├── TRANPOST.cbl          ← transaction posting
│   ├── INTCALC.cbl           ← interest calculation, calls IRD lookup
│   └── REPORTGEN.cbl         ← end-of-day report generator
├── copybooks/
│   ├── CUSTREC.cpy           ← v3.1 (current)
│   ├── CUSTREC_V27.cpy       ← v2.7 (historical, used to demo copybook drift)
│   ├── ACCTREC.cpy
│   ├── TRANREC.cpy
│   ├── DATEUTIL.cpy
│   └── ERRORCDS.cpy
├── jcl/
│   ├── CUST_DELETE_INACTIVE.JCL    ← the demo's hero job
│   ├── ACCT_OPEN_BATCH.JCL
│   ├── EOD_REPORT.JCL
│   ├── TRAN_POST_HOURLY.JCL
│   ├── BACKUP_CUST.JCL             ← template the auto-backup-generator clones
│   └── BAD_PROMOTE_EXAMPLE.JCL     ← intentionally broken for "what JJSCAN+ catches" screenshot
├── procs/
│   ├── DBLOAD.PROC
│   ├── REPORT.PROC
│   ├── BACKUP.PROC
│   └── COMMON.PROC
├── db2/
│   ├── ddl/
│   │   ├── CUST_MASTER.sql         ← table the protected-resource policy points at
│   │   ├── ACCT_MASTER.sql
│   │   ├── TRAN_HISTORY.sql
│   │   └── DORMANT_QUEUE.sql
│   ├── plans/
│   │   ├── CUSTPKG_INT1.bind
│   │   ├── CUSTPKG_INT2.bind
│   │   ├── CUSTPKG_INT3.bind
│   │   └── CUSTPKG_PROD.bind
│   └── seed/
│       ├── cust_master.csv         ← 5,000 synthetic customers
│       ├── acct_master.csv         ← 12,000 accounts
│       └── tran_history.csv        ← 80,000 transactions
├── regions/
│   ├── int1.yaml
│   ├── int2.yaml
│   ├── int3.yaml
│   ├── dev1.yaml
│   ├── dev2.yaml
│   ├── dev3.yaml
│   └── prod.yaml
├── runbooks/
│   ├── S0C7_CUSTPROC_age_calc.md   ← seeded for the demo's Scene 2 lookup
│   ├── SQLCODE_805_int2_bind.md
│   └── IEC141I_dataset_not_cataloged.md
└── _seed.sh                         ← one-shot rebuild of the whole corpus
```

## Seeded defects (the things Helios is supposed to catch)

These are deliberately planted so JJSCAN+ and ABEND Archaeologist always have something to demo:

| Defect | Where | Caught by | Demo step |
|---|---|---|---|
| Copybook drift `CUSTREC` v3.1 vs v2.7 | `int3` SYSLIB still points at v2.7 | JJSCAN+ rule `copybook_drift` | Scene 1, finding #2 |
| Missing PROC member `BACKUP` in `int3.PROCLIB` | int3 region profile | JJSCAN+ rule `missing_proc_member` | Scene 1 alt path |
| PROC override conflict on `SYSOUT` DD | `EOD_REPORT.JCL` step 3 vs step 5 | JJSCAN+ rule `proc_override_conflict` | Region Atlas alt demo |
| DB2 plan mismatch — bound to `CUSTPKG.INT2`, JCL references `CUSTPKG.INT3` | `BAD_PROMOTE_EXAMPLE.JCL` | JJSCAN+ rule `db2_plan_mismatch` | Standalone screenshot |
| S0C7 from null DOB row | `CUSTPROC.cbl` line 247 + seed row 14782 | ABEND Archaeologist | Scene 2 |
| Missing backup pair on `CUST_DELETE_INACTIVE.JCL` | The job itself | Confidence Score backup_gap | Scene 1, finding #1 |

## Region profile differences (the substitution playground)

The seven regions intentionally diverge in ways Region Atlas can show as a diff:

| Field | int1 | int2 | int3 | prod |
|---|---|---|---|---|
| HLQ | `CUST.INT1` | `CUST.INT2` | `CUST.INT3` | `CUST.PROD` |
| DB2 subsystem | `DBI1` | `DBI2` | `DBI3` | `DBP1` |
| BIND collection | `CUSTPKG.INT1` | `CUSTPKG.INT2` | `CUSTPKG.INT3` | `CUSTPKG.PROD` |
| RACF group | `INT1DEV` | `INT2DEV` | `INT3DEV` | `PRODOPS` |
| JES class | A | A | P | S |
| SYSOUT class | X | X | S | S |
| Scheduler queue | `BATCH_DEV` | `BATCH_DEV` | `BATCH_INT` | `BATCH_PROD` |
| GDG retention | 5 generations | 5 | 30 | 90 |
| Protected resources | none | none | `CUST.MASTER` | `CUST.MASTER`, `ACCT.MASTER`, `TRAN.HISTORY` |
| Confidence weights | default | default | strict (×1.5 critical) | strictest (×2 critical, +20 backup_gap) |

A promotion from any source to any target produces a deterministic, repeatable diff — which makes the demo non-flaky.

## Building the corpus

```bash
cd shared/sample-corpus
./_seed.sh
```

The script:

1. Downloads ingredients into `_cache/`.
2. Applies `patches/meridianbank.patch` — renames headers, stitches programs.
3. Generates 5k customers, 12k accounts, 80k transactions with deterministic seed `42`.
4. Writes the seven region YAMLs.
5. Plants the seeded defects.
6. Verifies SHA-256 of the final corpus matches `corpus.sha256` (so the demo is bit-exact across machines).

Total runtime: ~90 seconds. Total size: ~14 MB.

## Ground-truth metrics from this corpus

These are the numbers that go on the README landing page (run with `make benchmark`):

| Metric | Without Helios | With Helios |
|---|---|---|
| `CUST_DELETE_INACTIVE.JCL` int2 → int3 promotion | 47 min | 6 min |
| First-prod-run ABEND rate (sample of 20 JCL members across regions) | 18% | 0% |
| Mean time to ABEND root cause (Scene 2 reproduction × 10 runs) | 4.3 hr | 4 min |
| Region onboarding (new dev given int3 cold) | 2.5 days | 22 min |

These numbers are not aspirational — they are reproduced on the corpus by `make benchmark` and committed to `bench/results/` on every release. Judges who ask "where do those numbers come from" get pointed at this directory.

## Renaming policy

Anywhere we ingest external code, we rewrite:

- Author tags → `MeridianBank Core Banking Platform`
- Bank names → `MeridianBank`
- City names → `Hartford` (the fictional HQ)
- Date ranges → 2018–2026

This keeps screenshots clean and avoids any appearance of using a real bank's code. License attribution is preserved in `shared/sample-corpus/NOTICES.md`.

## Why this matters for judging

A working synthetic shop is the difference between *"here are some PowerPoint slides"* and *"watch me promote a job, here's the output, here's the audit log row, here's the runbook update."* It is what makes Helios feel like a product instead of a demo. Every minute spent on the corpus pays back fivefold in demo confidence.
