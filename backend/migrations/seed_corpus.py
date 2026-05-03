"""Multi-dataset corpus seeder for shop ``meridianbank.demo``.

Reads from the gitignored ``test dataset/helios_sample_dataset/`` tree —
never from a checked-in copy. The artifacts persisted into Cloudant are
parser-derived AST excerpts plus first-party metadata (region YAMLs,
hand-crafted ABEND dumps, scenario specs); none of the source files
themselves are committed or copied into the repository.

Three source packs feed the corpus:

* ``bankdemo``    — 01_BankDemo (Rocket EULA, proprietary)
* ``omp_course``  — 02_OMP_COBOL_Course (CC-BY-4.0)
* ``cobol_check`` — 03_cobol-check_samples (Apache 2.0)

The seeder is idempotent: every doc carries a deterministic ``_id`` so
re-running upserts. ``reset_demo_shop`` wipes the demo shop before a
re-seed when ``--reset`` is passed.

PUBLIC ENTRY POINTS
-------------------

* :func:`seed_all`            — seed everything for ``shop="meridianbank.demo"``
* :func:`seed_pack`           — seed a single source pack
* :func:`reset_demo_shop`     — wipe every doc whose ``shop`` is the demo shop
* :func:`compute_corpus_index` — denormalised summary doc per shop
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml

from app.config import get_settings
from app.services.cloudant import CloudantClient
from app.services.mainframe_parser import (
    GapLogger,
    parse_cobol,
    parse_ddl,
    parse_jcl,
    parse_pli,
    parse_proc,
)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = REPO_ROOT / "test dataset" / "helios_sample_dataset"
CORPUS_REGIONS = REPO_ROOT / "shared" / "sample-corpus" / "regions" / "bankdemo"
ABEND_EXAMPLES = REPO_ROOT / "shared" / "sample-corpus" / "abend_examples"

DEMO_SHOP = "meridianbank.demo"

SourcePack = Literal["bankdemo", "omp_course", "cobol_check"]

# Cloudant collections used by the corpus seeder. The legacy ``regions``,
# ``users``, ``audit_log``, etc. are seeded by ``seed_demo.py``; the
# corpus collections are additive.
NEW_DATABASES = [
    "regions",
    "jcl_artifacts",
    "cobol_artifacts",
    "pli_artifacts",
    "copybook_artifacts",
    "proc_artifacts",
    "sql_ddl_artifacts",
    "test_fixtures",
    "demo_scenarios",
    "corpus_index",
    "abend_patterns",
    "users",
    "learning",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _model_dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj  # type: ignore[return-value]


@dataclass
class SeedReport:
    """Counts produced by :func:`seed_all`. Returned for the verify step."""

    regions: int = 0
    jcl: int = 0
    cobol: int = 0
    pli: int = 0
    copybooks: int = 0
    procs: int = 0
    ddl_tables: int = 0
    ddl_views: int = 0
    fixtures: int = 0
    scenarios: int = 0
    abend_examples: int = 0
    users: int = 0
    learning_events: int = 0
    gaps: int = 0
    by_pack: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.by_pack is None:
            self.by_pack = defaultdict(int)


# ---------------------------------------------------------------------------
# Region seeding
# ---------------------------------------------------------------------------


async def _seed_corpus_regions(cloudant: CloudantClient) -> int:
    """Upsert every region YAML under ``regions/bankdemo/`` into shop ``meridianbank.demo``."""
    if not CORPUS_REGIONS.exists():
        return 0
    files = sorted(CORPUS_REGIONS.glob("*.yaml"))
    for f in files:
        profile = yaml.safe_load(f.read_text(encoding="utf-8"))
        name = profile["name"]
        doc = {
            "_id": f"region:{DEMO_SHOP}:{name}",
            "kind": "region",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            **profile,
        }
        await cloudant.put("regions", doc)
    return len(files)


# ---------------------------------------------------------------------------
# JCL / COBOL / PL/I / DDL / PROC seeding
# ---------------------------------------------------------------------------


async def _seed_jcl(
    cloudant: CloudantClient,
    files: Iterable[Path],
    *,
    pack: SourcePack,
    region: str,
    gap_logger: GapLogger,
) -> int:
    n = 0
    for jcl in files:
        try:
            text = jcl.read_text(encoding="utf-8", errors="replace")
            ast = parse_jcl(text, name=jcl.stem.upper(), source_path=str(jcl), gap_logger=gap_logger)
        except Exception as exc:  # noqa: BLE001
            gap_logger.record("jcl", str(jcl), f"unhandled: {exc}")
            continue
        doc = {
            "_id": f"jcl:{DEMO_SHOP}:{pack}:{jcl.stem.upper()}:{region}",
            "kind": "jcl_artifact",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            "source_pack": pack,
            "source_path": str(jcl.relative_to(DATASET_ROOT)).replace("\\", "/"),
            "name": jcl.stem.upper(),
            "region": region,
            "state": "open",
            "source_blob_sha256": _hash_text(text),
            "parsed": _model_dump(ast),
        }
        await cloudant.put("jcl_artifacts", doc)
        n += 1
    return n


async def _seed_cobol(
    cloudant: CloudantClient,
    files: Iterable[Path],
    *,
    pack: SourcePack,
    gap_logger: GapLogger,
) -> int:
    n = 0
    for cbl in files:
        try:
            text = cbl.read_text(encoding="utf-8", errors="replace")
            ast = parse_cobol(text, source_path=str(cbl), gap_logger=gap_logger)
        except Exception as exc:  # noqa: BLE001
            gap_logger.record("cobol", str(cbl), f"unhandled: {exc}")
            continue
        if ast.program_id == "UNKNOWN":
            # Likely a copybook member — route to copybook collection instead.
            continue
        doc = {
            "_id": f"cobol:{DEMO_SHOP}:{pack}:{ast.program_id}:{cbl.stem.upper()}",
            "kind": "cobol_artifact",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            "source_pack": pack,
            "source_path": str(cbl.relative_to(DATASET_ROOT)).replace("\\", "/"),
            "program_id": ast.program_id,
            "parsed": _model_dump(ast),
        }
        await cloudant.put("cobol_artifacts", doc)
        n += 1
    return n


async def _seed_pli(
    cloudant: CloudantClient,
    files: Iterable[Path],
    *,
    pack: SourcePack,
    gap_logger: GapLogger,
) -> int:
    n = 0
    for pli in files:
        try:
            text = pli.read_text(encoding="utf-8", errors="replace")
            ast = parse_pli(text, source_path=str(pli), gap_logger=gap_logger)
        except Exception as exc:  # noqa: BLE001
            gap_logger.record("pli", str(pli), f"unhandled: {exc}")
            continue
        doc = {
            "_id": f"pli:{DEMO_SHOP}:{pack}:{ast.procedure_name}:{pli.stem.upper()}",
            "kind": "pli_artifact",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            "source_pack": pack,
            "source_path": str(pli.relative_to(DATASET_ROOT)).replace("\\", "/"),
            "procedure_name": ast.procedure_name,
            "parsed": _model_dump(ast),
        }
        await cloudant.put("pli_artifacts", doc)
        n += 1
    return n


async def _seed_copybooks(
    cloudant: CloudantClient,
    *,
    files: Iterable[Path],
    pack: SourcePack,
    library_id: str,
    version: str = "v1",
) -> int:
    n = 0
    for cpy in files:
        text = cpy.read_text(encoding="utf-8", errors="replace")
        name = cpy.stem.upper()
        # The cobol-check pack pairs ``X.CBL`` with ``X-padded.CBL``;
        # store padded variants under their literal stem so a doc per
        # variant exists.
        version_tag = version
        base_name = name
        if name.endswith("-PADDED"):
            base_name = name.removesuffix("-PADDED")
            version_tag = f"{version}-padded"
        doc = {
            "_id": f"cpy:{DEMO_SHOP}:{pack}:{library_id}:{base_name}:{version_tag}",
            "kind": "copybook_artifact",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            "source_pack": pack,
            "source_path": str(cpy.relative_to(DATASET_ROOT)).replace("\\", "/"),
            "library_id": library_id,
            "name": base_name,
            "version": version_tag,
            "raw_text": text,
            "raw_sha256": _hash_text(text),
            "lines": len(text.splitlines()),
        }
        await cloudant.put("copybook_artifacts", doc)
        n += 1
    return n


async def _seed_procs(
    cloudant: CloudantClient,
    *,
    files: Iterable[Path],
    pack: SourcePack,
    library_id: str,
    gap_logger: GapLogger,
) -> int:
    n = 0
    for prc in files:
        try:
            text = prc.read_text(encoding="utf-8", errors="replace")
            ast = parse_proc(
                text,
                name=prc.stem.upper(),
                library_id=library_id,
                source_path=str(prc),
                gap_logger=gap_logger,
            )
        except Exception as exc:  # noqa: BLE001
            gap_logger.record("proc", str(prc), f"unhandled: {exc}")
            continue
        doc = {
            "_id": f"proc:{DEMO_SHOP}:{pack}:{library_id}:{ast.member}",
            "kind": "proc_artifact",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            "source_pack": pack,
            "source_path": str(prc.relative_to(DATASET_ROOT)).replace("\\", "/"),
            "library_id": library_id,
            "member": ast.member,
            "parsed": _model_dump(ast),
        }
        await cloudant.put("proc_artifacts", doc)
        n += 1
    return n


async def _seed_ddl(
    cloudant: CloudantClient,
    *,
    files: Iterable[Path],
    pack: SourcePack,
    dialect: Literal["db2", "xdb"],
    gap_logger: GapLogger,
) -> int:
    n = 0
    for sql in files:
        try:
            text = sql.read_text(encoding="utf-8", errors="replace")
            tables = parse_ddl(text, dialect=dialect, source_path=str(sql), gap_logger=gap_logger)
        except Exception as exc:  # noqa: BLE001
            gap_logger.record("sql_ddl", str(sql), f"unhandled: {exc}")
            continue
        for t in tables:
            doc = {
                "_id": f"ddl:{DEMO_SHOP}:{pack}:{dialect}:{t.name}",
                "kind": "sql_ddl_artifact",
                "schema_version": "1.0",
                "shop": DEMO_SHOP,
                "source_pack": pack,
                "source_path": str(sql.relative_to(DATASET_ROOT)).replace("\\", "/"),
                "dialect": dialect,
                "schema": t.schema_name,
                "table": t.name,
                "parsed": _model_dump(t),
            }
            await cloudant.put("sql_ddl_artifacts", doc)
            n += 1
    return n


# ---------------------------------------------------------------------------
# Per-pack drivers
# ---------------------------------------------------------------------------


async def seed_pack(
    cloudant: CloudantClient,
    pack: SourcePack,
    *,
    gap_logger: GapLogger | None = None,
) -> dict[str, int]:
    """Seed a single source pack and return per-collection counts."""

    gl = gap_logger or GapLogger()
    counts: dict[str, int] = defaultdict(int)

    if pack == "bankdemo":
        bd = DATASET_ROOT / "01_BankDemo"
        if not bd.exists():
            return dict(counts)
        # JCL into bnk_test_vsam (the demo's primary integration region).
        jcls = list((bd / "sources" / "jcl").glob("*.jcl"))
        counts["jcl"] += await _seed_jcl(
            cloudant, jcls, pack=pack, region="bnk_test_vsam", gap_logger=gl
        )
        # COBOL across core / data / data/sql / data/vsam.
        cobol_dirs = [
            bd / "sources" / "cobol" / "core",
            bd / "sources" / "cobol" / "data",
            bd / "sources" / "cobol" / "data" / "sql",
            bd / "sources" / "cobol" / "data" / "vsam",
        ]
        cbl_files: list[Path] = []
        for d in cobol_dirs:
            if d.exists():
                cbl_files.extend(d.glob("*.cbl"))
        counts["cobol"] += await _seed_cobol(cloudant, cbl_files, pack=pack, gap_logger=gl)
        # PL/I across main + fetchable.
        pli_files: list[Path] = []
        for d in [bd / "sources" / "pli" / "main", bd / "sources" / "pli" / "fetchable"]:
            if d.exists():
                pli_files.extend(d.glob("*.pli"))
        counts["pli"] += await _seed_pli(cloudant, pli_files, pack=pack, gap_logger=gl)
        # Copybooks.
        copybook_dir = bd / "sources" / "copybook"
        if copybook_dir.exists():
            cpys = list(copybook_dir.glob("*.cpy"))
            counts["copybooks"] += await _seed_copybooks(
                cloudant, files=cpys, pack=pack, library_id="bankdemo_copylib"
            )
        # Procs.
        proc_dir = bd / "sources" / "proclib"
        if proc_dir.exists():
            prcs = list(proc_dir.glob("*.prc"))
            counts["procs"] += await _seed_procs(
                cloudant, files=prcs, pack=pack, library_id="bankdemo_proclib", gap_logger=gl
            )
        # SQL DDL — both dialects.
        db2_dir = bd / "sources" / "sql" / "DB2_DDL"
        xdb_dir = bd / "sources" / "sql" / "XDB_DDL"
        if db2_dir.exists():
            sqls = list(db2_dir.glob("*.sql"))
            counts["ddl"] += await _seed_ddl(
                cloudant, files=sqls, pack=pack, dialect="db2", gap_logger=gl
            )
        if xdb_dir.exists():
            sqls = list(xdb_dir.glob("*.sql"))
            counts["ddl"] += await _seed_ddl(
                cloudant, files=sqls, pack=pack, dialect="xdb", gap_logger=gl
            )

    elif pack == "omp_course":
        omp = DATASET_ROOT / "02_OMP_COBOL_Course"
        if not omp.exists():
            return dict(counts)
        # JCL across labs_intermediate, labs_advanced, challenges_advanced.
        jcl_dirs = [
            omp / "labs_intermediate" / "jcl",
            omp / "labs_advanced" / "jcl",
            omp / "challenges_advanced" / "Debugging" / "jcl",
        ]
        jcls: list[Path] = []
        for d in jcl_dirs:
            if d.exists():
                jcls.extend(d.glob("*.jcl"))
        counts["jcl"] += await _seed_jcl(
            cloudant, jcls, pack=pack, region="training_int", gap_logger=gl
        )
        # COBOL programs (.cobol + .cbl).
        cbl_files: list[Path] = []
        for d in [
            omp / "labs_intermediate" / "cbl",
            omp / "labs_advanced" / "cbl",
            omp / "challenges_advanced" / "Debugging" / "cbl",
        ]:
            if d.exists():
                cbl_files.extend(d.glob("*.cobol"))
                cbl_files.extend(d.glob("*.cbl"))
        counts["cobol"] += await _seed_cobol(cloudant, cbl_files, pack=pack, gap_logger=gl)
        # Cataloged procs from labs_intermediate/jclproc + labs_advanced/jclproc.
        proc_files: list[Path] = []
        for d in [
            omp / "labs_intermediate" / "jclproc",
            omp / "labs_advanced" / "jclproc",
        ]:
            if d.exists():
                proc_files.extend(d.glob("*.jcl"))
        counts["procs"] += await _seed_procs(
            cloudant, files=proc_files, pack=pack, library_id="omp_proclib", gap_logger=gl
        )

    elif pack == "cobol_check":
        cc = DATASET_ROOT / "03_cobol-check_samples"
        if not cc.exists():
            return dict(counts)
        # COBOL programs at cobol/*.CBL; copy variants under cobol/copy.
        program_dir = cc / "cobol"
        cbl_files = list(program_dir.glob("*.CBL")) + list(program_dir.glob("*.cbl"))
        # Filter out things we treat as copybooks below.
        copybook_dir = program_dir / "copy"
        cbl_files = [p for p in cbl_files if copybook_dir not in p.parents]
        counts["cobol"] += await _seed_cobol(cloudant, cbl_files, pack=pack, gap_logger=gl)
        # Copybooks: every file in cobol/copy/ is a drift fixture variant.
        if copybook_dir.exists():
            cpy_files = list(copybook_dir.glob("*.CBL")) + list(copybook_dir.glob("*.cbl"))
            cpy_files += list(copybook_dir.glob("*.cpy"))
            # Recurse into Outrec/ as well.
            for sub in copybook_dir.iterdir():
                if sub.is_dir():
                    cpy_files += list(sub.glob("*.CBL"))
                    cpy_files += list(sub.glob("*.cpy"))
            counts["copybooks"] += await _seed_copybooks(
                cloudant,
                files=cpy_files,
                pack=pack,
                library_id="cobol_check_copylib",
            )

    counts["gaps"] = len(gl.entries)
    return dict(counts)


# ---------------------------------------------------------------------------
# Test fixtures (PART F): per-rule positive + negative.
# ---------------------------------------------------------------------------


TEST_FIXTURES: list[dict[str, Any]] = [
    # JJ-COPYBOOK-DRIFT-001
    {
        "rule_id": "JJ-COPYBOOK-DRIFT-001",
        "kind": "positive",
        "fixture_id": "cbankdat_vsam_vs_sql",
        "description": "CBANKDAT.cpy resolves to v_VSAM in bnk_test_vsam, v_SQL in bnk_test_sql.",
        "source_jcl": "ZBNKBAT1",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_test_sql",
        "expected_finding": True,
        "expected_severity": "high",
        "ground_truth_notes": "two seeded copybook versions for CBANKDAT differ in BALANCE field type",
    },
    {
        "rule_id": "JJ-COPYBOOK-DRIFT-001",
        "kind": "positive",
        "fixture_id": "badcopy_drift",
        "description": "BADCOPY.CBL from cobol-check intentionally has copybook content not matching its callers.",
        "source_program": "BADCOPY",
        "source_pack": "cobol_check",
        "expected_finding": True,
        "expected_severity": "high",
        "ground_truth_notes": "cobol-check ships BADCOPY.CBL with a deliberately broken COPY directive",
    },
    {
        "rule_id": "JJ-COPYBOOK-DRIFT-001",
        "kind": "negative",
        "fixture_id": "alpha_clean",
        "description": "ALPHA.CBL is a single-COPY program; should not fire copybook-drift in any region.",
        "source_program": "ALPHA",
        "source_pack": "cobol_check",
        "expected_finding": False,
    },
    # JJ-MISSING-PROC-MEMBER-001
    {
        "rule_id": "JJ-MISSING-PROC-MEMBER-001",
        "kind": "positive",
        "fixture_id": "ybattso_in_db2",
        "description": "ZBNKBAT1.jcl EXECs YBATTSO; promoted to bnk_db2 whose PROCLIB is omp_proclib (no YBATTSO).",
        "source_jcl": "ZBNKBAT1",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_db2",
        "expected_finding": True,
        "expected_severity": "high",
        "ground_truth_notes": "bnk_db2 carries omp_proclib only; YBATTSO is in bankdemo_proclib",
    },
    {
        "rule_id": "JJ-MISSING-PROC-MEMBER-001",
        "kind": "positive",
        "fixture_id": "igywclg_missing",
        "description": "OMP CBL0008J.jcl EXECs IGYWCLG; target region without IGYWCLG in PROCLIB → finding.",
        "source_jcl": "CBL0008J",
        "source_region": "training_int",
        "target_region": "bnk_test_vsam",
        "expected_finding": True,
        "expected_severity": "high",
    },
    {
        "rule_id": "JJ-MISSING-PROC-MEMBER-001",
        "kind": "negative",
        "fixture_id": "ybattso_in_test_vsam",
        "description": "ZBNKEXT1.jcl in bnk_test_vsam — PROCLIB has YBATTSO; no finding expected.",
        "source_jcl": "ZBNKEXT1",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_test_vsam",
        "expected_finding": False,
    },
    # JJ-PROC-OVERRIDE-CONFLICT-001
    {
        "rule_id": "JJ-PROC-OVERRIDE-CONFLICT-001",
        "kind": "positive",
        "fixture_id": "zbnkbat1_steplib_override",
        "description": "ZBNKBAT1.jcl EXTRACT step has a STEPLIB override conflicting with YBATTSO PROC default.",
        "source_jcl": "ZBNKBAT1",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_pac",
        "expected_finding": True,
        "expected_severity": "medium",
    },
    {
        "rule_id": "JJ-PROC-OVERRIDE-CONFLICT-001",
        "kind": "negative",
        "fixture_id": "hello_no_overrides",
        "description": "OMP HELLO.jcl is a single-step EXEC with no overrides; clean.",
        "source_jcl": "HELLO",
        "source_region": "training_int",
        "target_region": "training_int",
        "expected_finding": False,
    },
    # JJ-DB2-PLAN-MISMATCH-001
    {
        "rule_id": "JJ-DB2-PLAN-MISMATCH-001",
        "kind": "positive",
        "fixture_id": "myplan_in_pac",
        "description": "ZBNKBAT1.jcl runs PLAN(MYPLAN) on DB10; promoted to bnk_pac (DB20) where MYPLAN is not bound.",
        "source_jcl": "ZBNKBAT1",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_pac",
        "expected_finding": True,
        "expected_severity": "critical",
    },
    {
        "rule_id": "JJ-DB2-PLAN-MISMATCH-001",
        "kind": "positive",
        "fixture_id": "cbldb21r_in_training",
        "description": "labs_advanced/CBLDB21R.jcl binds against a plan not in training_int's bound set.",
        "source_jcl": "CBLDB21R",
        "source_region": "training_int",
        "target_region": "bnk_pac",
        "expected_finding": True,
        "expected_severity": "critical",
    },
    {
        "rule_id": "JJ-DB2-PLAN-MISMATCH-001",
        "kind": "negative",
        "fixture_id": "seltbl_in_training",
        "description": "labs_advanced/SELTBL.jcl run within training_int (its own DB2 collection); no mismatch.",
        "source_jcl": "SELTBL",
        "source_region": "training_int",
        "target_region": "training_int",
        "expected_finding": False,
    },
]


async def _seed_test_fixtures(cloudant: CloudantClient) -> int:
    for fx in TEST_FIXTURES:
        doc = {
            "_id": f"fx:{DEMO_SHOP}:{fx['rule_id']}:{fx['kind']}:{fx['fixture_id']}",
            "kind": "test_fixture",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            **fx,
        }
        await cloudant.put("test_fixtures", doc)
    return len(TEST_FIXTURES)


def _find_cobol_check_pairs() -> list[tuple[str, Path, Path]]:
    """Locate every ``X.CBL`` / ``X-padded.CBL`` pair in cobol-check.

    Returns a list of ``(base_name, plain_path, padded_path)``. The base
    name does not include the ``-padded`` suffix.
    """
    pairs: list[tuple[str, Path, Path]] = []
    cc_root = DATASET_ROOT / "03_cobol-check_samples" / "cobol"
    if not cc_root.exists():
        return pairs
    candidate_dirs = [cc_root, cc_root / "copy", cc_root / "copy" / "Outrec"]
    for d in candidate_dirs:
        if not d.exists():
            continue
        plain_files = {
            p.stem.upper(): p
            for p in list(d.glob("*.CBL")) + list(d.glob("*.cbl"))
            if not p.stem.upper().endswith("-PADDED")
        }
        for p in list(d.glob("*-padded.CBL")) + list(d.glob("*-padded.cbl")) + list(d.glob("*-PADDED.CBL")):
            base = p.stem.upper().removesuffix("-PADDED")
            plain = plain_files.get(base)
            if plain is not None:
                pairs.append((base, plain, p))
    return pairs


async def _seed_copybook_variant_fixtures(cloudant: CloudantClient) -> int:
    """One drift fixture per cobol-check pair so the rule has a guaranteed positive."""
    pairs = _find_cobol_check_pairs()
    n = 0
    for base, plain, padded in pairs:
        fx = {
            "rule_id": "JJ-COPYBOOK-DRIFT-001",
            "kind": "positive",
            "fixture_id": f"cobol_check_pair_{base}",
            "description": (
                f"cobol-check parallel variant: {plain.name} (v1) vs {padded.name} "
                "(v1-padded). Same logical copybook, divergent whitespace + sometimes "
                "divergent PIC clauses. The drift rule must surface this when the "
                "two regions resolve to different versions."
            ),
            "source_pack": "cobol_check",
            "source_paths": [
                str(plain.relative_to(DATASET_ROOT)).replace("\\", "/"),
                str(padded.relative_to(DATASET_ROOT)).replace("\\", "/"),
            ],
            "expected_finding": True,
            "expected_severity": "high",
            "ground_truth_notes": "intentional drift testbed shipped by cobol-check",
        }
        doc = {
            "_id": f"fx:{DEMO_SHOP}:JJ-COPYBOOK-DRIFT-001:positive:{fx['fixture_id']}",
            "kind": "test_fixture",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            **fx,
        }
        await cloudant.put("test_fixtures", doc)
        n += 1
    return n


async def _seed_copybook_variants_table(cloudant: CloudantClient) -> int:
    """One denormalised row per (copybook_name, version, source_pack) under
    ``corpus_index`` so the UI can render the drift-detection table without
    re-querying every copybook artifact.
    """
    res = await cloudant.find(
        "copybook_artifacts", {"shop": DEMO_SHOP}, limit=10000
    )
    rows: list[dict[str, Any]] = []
    for d in res.get("docs", []):
        rows.append(
            {
                "name": d.get("name"),
                "version": d.get("version"),
                "source_pack": d.get("source_pack"),
                "library_id": d.get("library_id"),
                "lines": d.get("lines"),
                "raw_sha256": d.get("raw_sha256"),
            }
        )
    doc = {
        "_id": f"copybook_variants_table:{DEMO_SHOP}",
        "kind": "copybook_variants_table",
        "schema_version": "1.0",
        "shop": DEMO_SHOP,
        "ts": _now_iso(),
        "rows": rows,
        "row_count": len(rows),
    }
    await cloudant.put("corpus_index", doc)
    return len(rows)


# ---------------------------------------------------------------------------
# Hero scenarios (PART E)
# ---------------------------------------------------------------------------


SCENARIOS: list[dict[str, Any]] = [
    {
        "scenario_id": "S1_ZBNKDEL_int_to_prod",
        "title": "ZBNKDEL.jcl: bnk_test_vsam → bnk_prod",
        "summary": "Hero arc — backup gap on BNKACC.PATH3 + JES class drift drives 62 → 94 → 100.",
        "source_artifact": "01_BankDemo/sources/jcl/ZBNKDEL.jcl",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_prod",
        "expected_findings": [
            {"rule_id": "BACKUP_GAP", "severity": "critical", "auto_fixable": True},
            {"rule_id": "JJ-COPYBOOK-DRIFT-001", "severity": "high", "auto_fixable": True},
            {"rule_id": "REGION_MISMATCH_JES_CLASS", "severity": "medium"},
        ],
        "expected_score_trajectory": [62, 94, 100],
    },
    {
        "scenario_id": "S2_ZBNKBAT1_int_to_pac",
        "title": "ZBNKBAT1.jcl: bnk_test_vsam → bnk_pac (all 4 JJSCAN+ rules fire)",
        "summary": "Copybook drift, missing PROC member, PROC override conflict, DB2 plan mismatch — all four rules fire on this single promote.",
        "source_artifact": "01_BankDemo/sources/jcl/ZBNKBAT1.jcl",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_pac",
        "expected_findings": [
            {"rule_id": "JJ-COPYBOOK-DRIFT-001", "severity": "high"},
            {"rule_id": "JJ-MISSING-PROC-MEMBER-001", "severity": "high"},
            {"rule_id": "JJ-PROC-OVERRIDE-CONFLICT-001", "severity": "medium"},
            {"rule_id": "JJ-DB2-PLAN-MISMATCH-001", "severity": "critical"},
        ],
        "expected_score_trajectory": [25],
    },
    {
        "scenario_id": "S3_DBANK01P_substitution",
        "title": "DBANK01P: bnk_test_vsam → bnk_db2 (substitution engine picks COBOL vs PL/I per region)",
        "summary": "Same logical program exists in COBOL and PL/I; the substitution engine selects per the target region's language_scope.",
        "source_artifact": "01_BankDemo/sources/cobol/data/sql/DBANK01P.cbl",
        "source_region": "bnk_test_vsam",
        "target_region": "bnk_db2",
        "expected_findings": [],
        "expected_score_trajectory": [88],
        "notes": "bnk_db2.language_scope=[cobol] picks the .cbl form; bnk_xdb.language_scope=[cobol,pli] would prefer the .pli form when both exist.",
    },
    {
        "scenario_id": "S4_ZBNKACC_schema_diff",
        "title": "Schema diff: bnk_db2 ↔ bnk_xdb on ZBNKACC table",
        "summary": "Same nine tables, two SQL dialects; the diff surfaces tablespace, IN DATABASE, and AUDIT clauses that differ.",
        "source_artifact": "01_BankDemo/sources/sql/DB2_DDL/ZBNKACC.sql",
        "source_region": "bnk_db2",
        "target_region": "bnk_xdb",
        "expected_findings": [
            {"rule_id": "SCHEMA_METADATA_DRIFT", "severity": "medium"}
        ],
        "expected_score_trajectory": [85],
    },
    {
        "scenario_id": "S5_CBL0106J_self_promote",
        "title": "CBL0106J.jcl: training_int self-promote (sandbox)",
        "summary": "OMP debugging exercise self-promote in the training sandbox; clean run, score 100, demonstrates the easy lane.",
        "source_artifact": "02_OMP_COBOL_Course/challenges_advanced/Debugging/jcl/CBL0106J.jcl",
        "source_region": "training_int",
        "target_region": "training_int",
        "expected_findings": [],
        "expected_score_trajectory": [100],
    },
]


async def _seed_scenarios(cloudant: CloudantClient) -> int:
    for sc in SCENARIOS:
        doc = {
            "_id": f"scn:{DEMO_SHOP}:{sc['scenario_id']}",
            "kind": "demo_scenario",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            **sc,
        }
        await cloudant.put("demo_scenarios", doc)
    return len(SCENARIOS)


# ---------------------------------------------------------------------------
# ABEND example dumps (PART G)
# ---------------------------------------------------------------------------


ABEND_DUMP_FIXTURES: list[dict[str, Any]] = [
    # Existing dumps already shipped under shared/sample-corpus/abend_examples/.
    # We add a corpus link doc per file so the pattern→example mapping is
    # queryable without scanning the filesystem.
    {
        "abend_code": "S0C7",
        "filename": "s0c7_bbank40p.txt",
        "failing_program": "BBANK40P",
        "failing_paragraph": "POPULATE-TXN-LIST",
        "failing_field": "BANK-SCREEN30-INPUT(-1)",
        "source_pack": "bankdemo",
        "source_path": "01_BankDemo/sources/cobol/core/BBANK40P.cbl",
        "ground_truth_notes": "OCCURS table accessed with subscript = -1 due to off-by-one on user input",
    },
    {
        "abend_code": "S0C7",
        "filename": "s0c7_cbl0106.txt",
        "failing_program": "CBL0106",
        "failing_paragraph": "PROCESS-RECORD",
        "failing_field": "ACCT-LIMIT",
        "source_pack": "omp_course",
        "source_path": "02_OMP_COBOL_Course/challenges_advanced/Debugging/cbl/CBL0106.cbl",
        "ground_truth_notes": "OMP debugging challenge — non-numeric input read from ACCTREC into a numeric field",
    },
    {
        "abend_code": "S0C4",
        "filename": "s0c4_dbank01p.txt",
        "failing_program": "DBANK01P",
        "failing_paragraph": "0500-READ-CUST",
        "failing_field": "CD01O-DATA",
        "source_pack": "bankdemo",
        "source_path": "01_BankDemo/sources/cobol/data/sql/DBANK01P.cbl",
        "ground_truth_notes": "REDEFINES mismatch on CD01O-DATA — accessing past the redefined area length",
    },
    {
        "abend_code": "S806",
        "filename": "s806_zbnkext1.txt",
        "failing_program": "ZBNKEXT1",
        "failing_paragraph": None,
        "failing_field": None,
        "source_pack": "bankdemo",
        "source_path": "01_BankDemo/sources/cobol/core",
        "ground_truth_notes": "STEPLIB DD does not include MFI01.MFIDEMO.LOADLIB; loader cannot find ZBNKEXT1",
    },
    {
        "abend_code": "IGZ0035S",
        "filename": "igz0035s_paragraph_not_found.txt",
        "failing_program": "MOCKPARA",
        "failing_paragraph": "ENTRY-DELETED-PARA",
        "failing_field": None,
        "source_pack": "cobol_check",
        "source_path": "03_cobol-check_samples/cobol/MOCKPARA.CBL",
        "ground_truth_notes": "PERFORM target removed without updating callers — common cobol-check test",
    },
    {
        "abend_code": "SQLCODE-805",
        "filename": "sqlcode_805_dbank01p_vsam_in_db2_region.txt",
        "failing_program": "DBANK01P",
        "failing_paragraph": "0600-FETCH-CUST",
        "failing_field": None,
        "source_pack": "bankdemo",
        "source_path": "01_BankDemo/sources/cobol/data/sql/DBANK01P.cbl",
        "ground_truth_notes": "VSAM-variant DBANK01P deployed into a DB2 region; plan not bound in DB10 collection",
    },
    {
        "abend_code": "SQLCODE-922",
        "filename": "sqlcode_922_racf_grant_missing.txt",
        "failing_program": "DBANK01P",
        "failing_paragraph": None,
        "failing_field": None,
        "source_pack": "bankdemo",
        "source_path": "01_BankDemo/sources/cobol/data/sql/DBANK01P.cbl",
        "ground_truth_notes": "RACF user lacks SELECT grant on BNKCUST in target catalog",
    },
]


async def _seed_abend_examples(cloudant: CloudantClient) -> int:
    """Write a corpus link doc per ABEND example.

    The pattern matcher (Bob's stub) reads ``helios_abend_patterns``; this
    seeder only records the example→program mapping so the corpus_search
    MCP tool can return them.
    """
    for ex in ABEND_DUMP_FIXTURES:
        path = ABEND_EXAMPLES / ex["filename"]
        body = path.read_text(encoding="utf-8") if path.exists() else ""
        doc = {
            "_id": f"abend_example:{DEMO_SHOP}:{ex['filename']}",
            "kind": "abend_example",
            "schema_version": "1.0",
            "shop": DEMO_SHOP,
            "dump_text": body,
            "exists_on_disk": path.exists(),
            **ex,
        }
        await cloudant.put("abend_patterns", doc)
    return len(ABEND_DUMP_FIXTURES)


# ---------------------------------------------------------------------------
# Demo users + dissent events for the new shop
# ---------------------------------------------------------------------------


_DEMO_USERS = [
    {
        "_id": f"user:{DEMO_SHOP}:maya",
        "kind": "user",
        "shop": DEMO_SHOP,
        "email": "maya@meridianbank.demo",
        "display_name": "Maya Patel",
        "roles": ["developer"],
    },
    {
        "_id": f"user:{DEMO_SHOP}:anil",
        "kind": "user",
        "shop": DEMO_SHOP,
        "email": "anil@meridianbank.demo",
        "display_name": "Anil Verma",
        "roles": ["reviewer", "developer"],
    },
    {
        "_id": f"user:{DEMO_SHOP}:raj",
        "kind": "user",
        "shop": DEMO_SHOP,
        "email": "raj@meridianbank.demo",
        "display_name": "Raj Iyer",
        "roles": ["release_manager", "reviewer", "developer"],
    },
    {
        "_id": f"user:{DEMO_SHOP}:svc",
        "kind": "user",
        "shop": DEMO_SHOP,
        "email": "svc@meridianbank.demo",
        "display_name": "Helios Service",
        "roles": ["service"],
    },
]


async def _seed_demo_users(cloudant: CloudantClient) -> int:
    for u in _DEMO_USERS:
        await cloudant.put("users", {**u, "schema_version": "1.0"})
    return len(_DEMO_USERS)


async def _seed_demo_dissent(cloudant: CloudantClient) -> int:
    """Nine prior dissent events on JJ-COPYBOOK-DRIFT-001 in the new shop."""
    from datetime import timedelta

    base = datetime.now(timezone.utc) - timedelta(days=30)
    docs: list[dict[str, Any]] = []
    for i in range(7):
        ts = base + timedelta(days=i * 2)
        ts_iso = ts.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        docs.append(
            {
                "_id": f"lrn:{DEMO_SHOP}:JJ-COPYBOOK-DRIFT-001:dismiss:{i}",
                "kind": "learning_event",
                "shop": DEMO_SHOP,
                "schema_version": "1.0",
                "type": "feedback_jjscan_dismissed",
                "rule_id": "JJ-COPYBOOK-DRIFT-001",
                "decision": "dismiss",
                "reason_tags": ["accepted_drift"],
                "actor": "maya@meridianbank.demo",
                "ts": ts_iso,
                "ts_unix_ms": int(ts.timestamp() * 1000),
            }
        )
    for i in range(2):
        ts = base + timedelta(days=14 + i * 2)
        ts_iso = ts.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        docs.append(
            {
                "_id": f"lrn:{DEMO_SHOP}:JJ-COPYBOOK-DRIFT-001:accept:{i}",
                "kind": "learning_event",
                "shop": DEMO_SHOP,
                "schema_version": "1.0",
                "type": "feedback_jjscan_accept",
                "rule_id": "JJ-COPYBOOK-DRIFT-001",
                "decision": "accept",
                "reason_tags": [],
                "actor": "anil@meridianbank.demo",
                "ts": ts_iso,
                "ts_unix_ms": int(ts.timestamp() * 1000),
            }
        )
    for d in docs:
        await cloudant.put("learning", d)
    return len(docs)


# ---------------------------------------------------------------------------
# Corpus index (denormalised summary)
# ---------------------------------------------------------------------------


async def compute_corpus_index(cloudant: CloudantClient, report: SeedReport) -> dict[str, Any]:
    doc = {
        "_id": f"corpus_index:{DEMO_SHOP}",
        "kind": "corpus_index",
        "schema_version": "1.0",
        "shop": DEMO_SHOP,
        "ts": _now_iso(),
        "regions": report.regions,
        "jcl_artifacts": report.jcl,
        "cobol_artifacts": report.cobol,
        "pli_artifacts": report.pli,
        "copybook_artifacts": report.copybooks,
        "proc_artifacts": report.procs,
        "sql_ddl_artifacts": report.ddl_tables,
        "test_fixtures": report.fixtures,
        "demo_scenarios": report.scenarios,
        "abend_examples": report.abend_examples,
        "by_pack": dict(report.by_pack),
        "summary": (
            f"Loaded: {report.by_pack.get('bankdemo_jcl', 0)} BankDemo JCL, "
            f"{report.by_pack.get('omp_course_jcl', 0)} OMP Course JCL, "
            f"{report.by_pack.get('cobol_check_cobol', 0)} cobol-check programs, "
            f"{report.ddl_tables} DDLs, {report.copybooks} copybooks."
        ),
    }
    await cloudant.put("corpus_index", doc)
    return doc


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


async def reset_demo_shop(cloudant: CloudantClient) -> int:
    """Wipe every doc whose ``shop`` equals :data:`DEMO_SHOP`."""
    n = 0
    for db in NEW_DATABASES:
        try:
            res = await cloudant.find(db, {"shop": DEMO_SHOP}, limit=10000)
        except Exception:
            continue
        for d in res.get("docs", []):
            try:
                await cloudant.delete(db, d["_id"], d.get("_rev", ""))
                n += 1
            except Exception:
                continue
    return n


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


async def seed_all(
    cloudant: CloudantClient,
    *,
    packs: list[SourcePack] | None = None,
    flush_gaps: bool = True,
) -> SeedReport:
    """Seed regions, the three packs, fixtures, scenarios, ABEND examples, and the corpus index."""

    for db in NEW_DATABASES:
        await cloudant.ensure_database(db)

    gl = GapLogger()
    report = SeedReport()

    report.regions += await _seed_corpus_regions(cloudant)
    report.users += await _seed_demo_users(cloudant)

    pack_names = packs if packs is not None else ["bankdemo", "omp_course", "cobol_check"]
    for pack in pack_names:
        counts = await seed_pack(cloudant, pack, gap_logger=gl)
        report.jcl += counts.get("jcl", 0)
        report.cobol += counts.get("cobol", 0)
        report.pli += counts.get("pli", 0)
        report.copybooks += counts.get("copybooks", 0)
        report.procs += counts.get("procs", 0)
        report.ddl_tables += counts.get("ddl", 0)
        report.by_pack[f"{pack}_jcl"] = counts.get("jcl", 0)
        report.by_pack[f"{pack}_cobol"] = counts.get("cobol", 0)
        report.by_pack[f"{pack}_pli"] = counts.get("pli", 0)
        report.by_pack[f"{pack}_copybooks"] = counts.get("copybooks", 0)
        report.by_pack[f"{pack}_procs"] = counts.get("procs", 0)
        report.by_pack[f"{pack}_ddl"] = counts.get("ddl", 0)

    report.fixtures += await _seed_test_fixtures(cloudant)
    report.fixtures += await _seed_copybook_variant_fixtures(cloudant)
    report.scenarios += await _seed_scenarios(cloudant)
    report.abend_examples += await _seed_abend_examples(cloudant)
    report.learning_events += await _seed_demo_dissent(cloudant)
    report.gaps = len(gl.entries)

    await compute_corpus_index(cloudant, report)
    await _seed_copybook_variants_table(cloudant)

    if flush_gaps:
        gl.flush()

    return report


async def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    settings = get_settings()
    cloudant = CloudantClient(settings)

    if "--reset" in args:
        wiped = await reset_demo_shop(cloudant)
        print(f"reset wiped {wiped} docs in shop {DEMO_SHOP}")

    pack_filter: list[SourcePack] | None = None
    if "--pack" in args:
        idx = args.index("--pack")
        pack_filter = [args[idx + 1]]  # type: ignore[list-item]

    report = await seed_all(cloudant, packs=pack_filter)

    print(json.dumps({
        "shop": DEMO_SHOP,
        "regions": report.regions,
        "users": report.users,
        "jcl": report.jcl,
        "cobol": report.cobol,
        "pli": report.pli,
        "copybooks": report.copybooks,
        "procs": report.procs,
        "ddl_tables": report.ddl_tables,
        "fixtures": report.fixtures,
        "scenarios": report.scenarios,
        "abend_examples": report.abend_examples,
        "learning_events": report.learning_events,
        "gaps": report.gaps,
        "by_pack": dict(report.by_pack),
    }, indent=2))

    await cloudant.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
