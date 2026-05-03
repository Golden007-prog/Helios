# BankDemo Integration — Real-Data Corpus for the Helios Demo

## Why this dataset

The `test dataset/helios_sample_dataset/01_BankDemo/` tree is the Rocket Software BankDemo application (formerly the Micro Focus BankDemo) — a long-standing, well-known mainframe demonstration codebase that any z/OS practitioner on the judging panel will recognise. Anchoring Helios to real BankDemo artefacts instead of fabricated MeridianBank files materially strengthens the demo:

- Judges see real CICS-era COBOL, real VSAM datasets, real CTL cards, real DB2 SUBSYS lines, real PROC chains.
- The dual-implementation pattern (`sources/cobol/data/sql/` vs `sources/cobol/data/vsam/` — same program names, different storage backend) is a textbook Region Atlas use case.
- `ZBNKDEL.jcl` issues `DELETE MFI01V.MFIDEMO.BNKACC.PATH3 PATH PURGE` against a real VSAM resource — perfect for the Confidence Score `backup_gap` penalty demo.
- `ZBNKBAT1.jcl` runs `DSN SYSTEM(DB10) RUN PROGRAM(ZBNKEXT1) PLAN(MYPLAN)` — perfect for JJSCAN+ `JJ-DB2-PLAN-MISMATCH-001`.
- `02_OMP_COBOL_Course/challenges_advanced/Debugging/` contains JCL designed to ABEND — perfect for ABEND Archaeologist Scene 2.

The MeridianBank narrative remains intact: MeridianBank is now defined as *"a fictional retail bank whose batch subsystem is the Rocket BankDemo."* Maya is still Maya. `CUST_DELETE_INACTIVE.JCL` becomes an alias for `ZBNKDEL.jcl` in the demo seed.

---

## Asset inventory

| Path | Count | Becomes in Helios |
|---|---|---|
| `01_BankDemo/sources/jcl/*.jcl` | 13 | Seeded JCL members for the demo regions |
| `01_BankDemo/sources/cobol/core/*.cbl` | 47 | Core CICS programs — link-edit targets for STEPLIB |
| `01_BankDemo/sources/cobol/data/sql/*.cbl` | 14 | SQL-backed DB access programs (used by `bnk_test_sql`) |
| `01_BankDemo/sources/cobol/data/vsam/*.cbl` | 16 | VSAM-backed DB access programs (used by `bnk_test_vsam`) |
| `01_BankDemo/sources/copybook/*.cpy` | 30+ | SYSLIB members — `copybook_drift` rule walks these |
| `01_BankDemo/datafiles/*.dat` | 5 | VSAM file content — protected resources for `backup_gap` |
| `01_BankDemo/scripts/config/env*.json` | 5 | Source data for region YAML profiles |
| `01_BankDemo/scripts/datasets_vsam/*.json` | 12 | VSAM dataset definitions — `protected_resources` entries |
| `01_BankDemo/scripts/config/CSD/*.json` | 6 | CICS resource defs (Phase-2 scope) |
| `02_OMP_COBOL_Course/challenges_advanced/Debugging/jcl/CBL0106J.jcl` | 1 | Scene 2 ABEND scenario seed |

---

## Region map — five regions from real configs

Drop these YAMLs into `shared/sample-corpus/regions/`. Each derives from one of the BankDemo `env*.json` configs.

### `bnk_dev_vsam`
Source: `scripts/config/env.json`. Storage: VSAM only, no DB2. HLQ: `MFI01D.MFIDEMO`. RACF group: `BNKDEV`. Use: developer sandbox.

### `bnk_test_vsam`
Source: `scripts/config/env.json` + test overrides. Storage: VSAM. HLQ: `MFI01T.MFIDEMO`. DB2 subsystem: `DB10`. JES class: `T`. Volser: `TST*`. Protected resources: `BNKACC`, `BNKCUST`, `BNKTXN`, `BNKHELP`, `BNKATYPE` (VSAM clusters). Use: integration test.

### `bnk_test_sql`
Source: `scripts/config/env_pg_pac.json`. Storage: PostgreSQL via MFDBFH. HLQ: `MFI01T.MFIDEMO`. DB2 subsystem: `DB10`. JES class: `T`. Protected resources: `bankdemo` (PostgreSQL DB), `CTLCARDS`, `EXTLIB`. Use: integration test (SQL backend).

### `bnk_pac`
Source: `scripts/config/env_mfdbfh.json`. Storage: PostgreSQL via MFDBFH (Performance Availability Cluster). HLQ: `MFI01P.MFIDEMO`. DB2 subsystem: `DB20`. RACF group: `BNKPAC`. JES class: `A`. Use: pre-prod cluster validation.

### `bnk_prod`
Source: hardened from `env_mfdbfh.json`. Storage: PostgreSQL via MFDBFH, replicated. HLQ: `MFI01.MFIDEMO` (no env suffix in prod, by convention). DB2 subsystem: `DB30`. RACF group: `BNKPROD`. JES class: `P` (long-running). Confidence weights: `critical=50`, `backup_gap=60` (stricter). Override required role: `release_manager`. Use: production.

### The 7 fields that differ between `bnk_test_vsam` and `bnk_prod`

Per `docs/PERSONA_MAYA.md` Scene 1, the diff must surface exactly 7 highlighted fields. Tune the seeded YAMLs so these — and only these — differ:

1. `hlq.application`: `MFI01T.MFIDEMO` → `MFI01.MFIDEMO`
2. `db2.subsystem`: `DB10` → `DB30`
3. `db2.collection`: `MFIDEMO_T` → `MFIDEMO_P`
4. `jes.class`: `T` → `P`
5. `racf.user_default`: `BNKDEV` → `BNKPROD`
6. `volser.primary`: `TST*` → `PRD*`
7. `gating.override_required_role`: `developer` → `release_manager`

Hold every other field identical between the two profiles. The diff demo's "exactly 7" assertion in `backend/tests/test_region_atlas.py` becomes a real test against the seeded data.

---

## Hero JCL — `ZBNKDEL.jcl`

This is the demo's centrepiece. It's small enough to fit on screen and contains the destructive DELETE that triggers the `backup_gap` penalty.

```
//BACPATH  JOB MFIDEMO,MFIDEMO,CLASS=A,MSGCLASS=A
//STEP2    EXEC PGM=IDCAMS,REGION=512K
//SYSPRINT DD   SYSOUT=A
//SYSIN    DD   *
         DELETE  -
           MFI01V.MFIDEMO.BNKACC.PATH3 -
           PATH PURGE
//
```

Why it's perfect:

- 12 lines — fits on a slide
- Real DELETE against a real protected resource (`BNKACC.PATH3`)
- Promoting `bnk_test_vsam` → `bnk_prod` will trigger:
  - `backup_gap` penalty (−30) — `BNKACC` is in `bnk_prod`'s `protected_resources`
  - `region_mismatch` on JES class T → P (−8)
  - `copybook_drift` finding (−5) — `CBANKDAT.cpy` v_VSAM vs v_SQL
- Auto-fixes available: `generate_paired_backup` (IDCAMS REPRO of `BNKACC.PATH3` → `MFI01.MFIDEMO.BAK.BNKACC.D26122.T161203`)

**Scoring trajectory.** 100 − 30 (backup_gap) − 8 (region_mismatch) = **62**. After accepting the auto-backup → **94**. After accepting the copybook fix (recomputes without the −5 high finding) → **100**. The 62 → 94 → 100 from `PERSONA_MAYA.md` Scene 1 holds without further tuning.

---

## Companion JCL for JJSCAN+ rule coverage

Use `ZBNKBAT1.jcl` as the second-on-screen example to show all four rules firing simultaneously when promoted `bnk_test_vsam` → `bnk_pac`:

- `JJ-COPYBOOK-DRIFT-001` — `CBANKDAT.cpy` resolves to v_VSAM in `bnk_test_vsam`, v_SQL in `bnk_pac` (seed two versions in the SYSLIB chains)
- `JJ-MISSING-PROC-MEMBER-001` — `EXEC YBATTSO` references a PROC not in `bnk_pac`'s PROCLIB (seed YBATTSO only in `bnk_test_vsam`'s PROCLIB)
- `JJ-PROC-OVERRIDE-CONFLICT-001` — STEPLIB override on the `EXTRACT` step conflicts with the PROC-level STEPLIB
- `JJ-DB2-PLAN-MISMATCH-001` — `PLAN(MYPLAN)` references a plan not bound in `bnk_pac`'s DB20 collection

This gives the demo a "show me the depth" moment after the hero promote.

---

## Scene 2 — ABEND Archaeologist

`CBL0106J.jcl` is the seed scenario — it reads `&SYSUID..DATA` which can be set up to fail.

Better: hand-craft a S0C7 dump fragment from `BBANK40P.cbl` (the deposit/withdrawal program) where a numeric MOVE on an uninitialised field fails. Save as `shared/sample-corpus/abend_examples/s0c7_bbank40p.txt`:

```
IGZ0035S The reference to table BANK-SCREEN30-INPUT (subscript = -1)
        attempted to use a subscript value not within the permitted range
        From compile unit BBANK40P at entry point BBANK40P at compile
        unit offset +0x000003D8
PSW=078D2400 80003D78
ABEND CODE 0C7
```

The classifier identifies `S0C7` + maps PSW offset to a specific line in `BBANK40P.cbl` + walks the MOVE chain back to a READ on `BNKCUST` that returned NULL for the address-line field. Granite Code 8B summarises the data trace into Maya's plain-English explanation.

---

## Seed loader sequence

Add to `backend/migrations/seed_demo.py`:

```
1. Copy 01_BankDemo/sources/jcl/*.jcl                → shared/sample-corpus/jcl/
2. Copy 01_BankDemo/sources/copybook/*.cpy           → shared/sample-corpus/copylib/
3. Copy 01_BankDemo/sources/cobol/**/*.cbl           → shared/sample-corpus/cobol/
4. Copy 01_BankDemo/datafiles/*.dat                  → shared/sample-corpus/data/
5. Generate 5 region YAMLs (above)                   → shared/sample-corpus/regions/
6. For each JCL, parse + write a helios_jcl_artifacts row
   (program refs, COPY statements, STEPLIB refs, PROC refs, DB2 SUBSYS lines)
7. Generate 9 prior-dissent events on JJ-COPYBOOK-DRIFT-001 firing
   on CBANKDAT.cpy in bnk_test_vsam (the "7 of 9 dismissed" demo line)
8. Seed the 15 ABEND patterns + s0c7_bbank40p.txt example dump
9. Verify:
   - /api/regions returns 5
   - /api/regions/bnk_test_vsam/diff/bnk_prod returns 7 fields
   - /api/scan?jcl=ZBNKDEL.jcl&source=bnk_test_vsam&target=bnk_prod returns score=62
```

The script must be idempotent.

---

## Updates to existing docs (minimal)

Small edits to align the narrative without rewriting:

- `docs/PERSONA_MAYA.md` Scene 1: change `CUST_DELETE_INACTIVE.JCL` to `ZBNKDEL.jcl (the BNKACC.PATH3 cleanup)`; replace the 7-substitutions list with the seven fields above.
- `docs/CORPUS.md`: add a section "Source dataset — Rocket BankDemo" pointing at this doc.
- `docs/DEMO_SCRIPT.md`: update the JCL filename references and the score-breakdown lines.
- `shared/sample-corpus/MERIDIANBANK/`: this directory becomes a thin alias layer over the BankDemo files (or is removed entirely — your call).

---

## Demo dry-run checklist

Print this; tape it next to the demo laptop.

1. Backend up: `make dev-backend` — verify `/healthz` returns ok
2. Frontend up: `make dev-frontend` — verify `localhost:3000` renders shell
3. Seed loaded: `make seed && curl localhost:8080/api/regions | jq '.regions | length'` returns `5`
4. Helios → Atlas → click `bnk_test_vsam`
5. Click **Diff with bnk_prod** → 7 fields highlighted in under 250 ms
6. Helios → Studio → open `ZBNKDEL.jcl`
7. Click **Promote** → wizard pops, source `bnk_test_vsam`, target `bnk_prod`
8. **Confidence Score = 62, RED.** Top reasons listed (backup gap, JES class, copybook drift)
9. Click **Auto-fix the backup gap** → score → **94**
10. Click the copybook drift finding → review side-by-side → **Apply auto-fix** → score → **100**
11. Click **Promote** → toast on Anil's phone (split-screen demo moment)
12. Anil approves on second device → audit log entry visible in main UI
13. Switch to **ABEND** tab → paste `s0c7_bbank40p.txt` → three-pane analysis renders
14. Total elapsed: under 2 minutes

---

## What this doc is NOT

- Not the demo script — that's `docs/DEMO_SCRIPT.md`
- Not the corpus inventory — that's `docs/CORPUS.md`
- Not the region schema — that's `docs/REGION_PROFILE_SCHEMA.md`
- Not the seed implementation — that's `backend/migrations/seed_demo.py`

---

## One sentence

> Rocket BankDemo becomes Helios's real-data corpus; `ZBNKDEL.jcl` is the hero, five regions derive from the existing BankDemo `env*.json` configs, the 62 → 94 → 100 trajectory holds with the seven listed field differences, and a hand-crafted S0C7 from `BBANK40P.cbl` anchors Scene 2.
