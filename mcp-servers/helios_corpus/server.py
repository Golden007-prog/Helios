"""helios-corpus MCP server — read-only access to the seeded Helios corpus.

Backed by the same Cloudant collections that ``backend/migrations/seed_corpus.py``
writes. Tools are scoped to one shop (``DEMO_SHOP``, default ``meridianbank.demo``).
The seeder owns the source-of-truth artifacts; this server is a query layer.

Tools exposed:

* ``corpus_list_regions``   — eight region names with one-line descriptions
* ``corpus_list_jcl``       — filtered JCL list (region, source_pack)
* ``corpus_get_jcl``        — raw text + parsed AST for one JCL
* ``corpus_get_copybook``   — raw text + AST for a copybook (with version)
* ``corpus_search``         — fuzzy-substring search across the corpus
* ``corpus_diff_schema``    — DDL diff between two dialect-tagged tables
* ``corpus_scenarios``      — the five hero scenarios from PART E
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Allow ``python -m helios_corpus.server`` to find the backend modules.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from _shared import ToolError, ToolRegistry, run_cli  # noqa: E402  (sys.path mutation above must run first)

DEMO_SHOP = os.environ.get("HELIOS_DEMO_SHOP", "meridianbank.demo")


registry = ToolRegistry(
    server_name="helios-corpus",
    description=f"Read-only access to the Helios corpus for shop {DEMO_SHOP!r}.",
)


# ---------------------------------------------------------------------------
# Cloudant client (lazy + cached)
# ---------------------------------------------------------------------------


_client: Any | None = None


async def _get_cloudant() -> Any:
    global _client
    if _client is None:
        # Force in-memory mode in environments without IBM Cloud creds — the
        # seed has to have run in the same process for the data to be visible.
        # In production the live Cloudant client is used.
        from app.config import get_settings  # type: ignore[import-not-found]
        from app.services.cloudant import CloudantClient  # type: ignore[import-not-found]

        _client = CloudantClient(get_settings())
    return _client


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def _list_regions() -> dict[str, Any]:
    cl = await _get_cloudant()
    res = await cl.find("regions", {"shop": DEMO_SHOP, "kind": "region"}, limit=100)
    rows = []
    for d in res.get("docs", []):
        rows.append(
            {
                "name": d["name"],
                "tier": d.get("tier"),
                "source_pack": d.get("source_pack"),
                "description": d.get("description", ""),
            }
        )
    rows.sort(key=lambda r: r["name"])
    return {"regions": rows, "total": len(rows)}


async def _list_jcl(
    region: str | None = None,
    source_pack: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    cl = await _get_cloudant()
    selector: dict[str, Any] = {"shop": DEMO_SHOP, "kind": "jcl_artifact"}
    if region:
        selector["region"] = region
    if source_pack:
        selector["source_pack"] = source_pack
    limit = max(1, min(200, int(limit or 20)))
    res = await cl.find("jcl_artifacts", selector, limit=limit)
    items = [
        {
            "name": d.get("name"),
            "region": d.get("region"),
            "source_pack": d.get("source_pack"),
            "source_path": d.get("source_path"),
            "step_count": len((d.get("parsed") or {}).get("steps") or []),
        }
        for d in res.get("docs", [])
    ]
    return {"items": items, "total": len(items)}


async def _get_jcl(name: str, region: str | None = None) -> dict[str, Any]:
    if not name:
        raise ToolError("'name' is required", code="INVALID_ARGUMENT")
    cl = await _get_cloudant()
    selector: dict[str, Any] = {
        "shop": DEMO_SHOP,
        "kind": "jcl_artifact",
        "name": name.upper(),
    }
    if region:
        selector["region"] = region
    res = await cl.find("jcl_artifacts", selector, limit=5)
    docs = res.get("docs", [])
    if not docs:
        raise ToolError(f"JCL {name!r} not found", code="NOT_FOUND")
    d = docs[0]
    return {
        "name": d["name"],
        "region": d.get("region"),
        "source_pack": d.get("source_pack"),
        "source_path": d.get("source_path"),
        "source_blob_sha256": d.get("source_blob_sha256"),
        "parsed": d.get("parsed"),
    }


async def _get_copybook(name: str, version: str | None = None) -> dict[str, Any]:
    if not name:
        raise ToolError("'name' is required", code="INVALID_ARGUMENT")
    cl = await _get_cloudant()
    selector: dict[str, Any] = {
        "shop": DEMO_SHOP,
        "kind": "copybook_artifact",
        "name": name.upper(),
    }
    if version:
        selector["version"] = version
    res = await cl.find("copybook_artifacts", selector, limit=10)
    docs = res.get("docs", [])
    if not docs:
        raise ToolError(f"copybook {name!r} not found", code="NOT_FOUND")
    return {
        "variants": [
            {
                "name": d["name"],
                "version": d.get("version"),
                "source_pack": d.get("source_pack"),
                "library_id": d.get("library_id"),
                "lines": d.get("lines"),
                "raw_sha256": d.get("raw_sha256"),
                "raw_text": d.get("raw_text"),
            }
            for d in docs
        ],
        "total": len(docs),
    }


async def _search(query: str, kind: str | None = None, limit: int = 20) -> dict[str, Any]:
    if not query:
        raise ToolError("'query' is required", code="INVALID_ARGUMENT")
    cl = await _get_cloudant()
    needle = query.lower()
    limit = max(1, min(100, int(limit or 20)))
    hits: list[dict[str, Any]] = []

    def _haystack_text(doc: dict[str, Any]) -> str:
        """Build a flat string for substring scanning across surface fields
        plus relevant nested AST fragments."""
        parts: list[str] = []
        for fld in ("name", "program_id", "procedure_name", "source_path", "raw_text"):
            v = doc.get(fld)
            if isinstance(v, str):
                parts.append(v)
        parsed = doc.get("parsed") or {}
        for fld in ("steplib_dsns", "pgm_refs", "proc_refs"):
            v = parsed.get(fld)
            if isinstance(v, list):
                parts.extend(str(x) for x in v)
        for step in parsed.get("steps") or []:
            for dd in step.get("dd_statements", []) or []:
                if dd.get("dsn"):
                    parts.append(str(dd["dsn"]))
        for cs in parsed.get("copy_statements") or []:
            if cs.get("name"):
                parts.append(str(cs["name"]))
        return " | ".join(parts)

    async def _scan(short_db: str, kind_filter: str) -> None:
        if kind and kind != kind_filter:
            return
        res = await cl.find(short_db, {"shop": DEMO_SHOP, "kind": kind_filter}, limit=500)
        for d in res.get("docs", []):
            haystack = _haystack_text(d).lower()
            if needle in haystack:
                hits.append(
                    {
                        "kind": kind_filter,
                        "name": d.get("name") or d.get("program_id") or d.get("procedure_name"),
                        "source_pack": d.get("source_pack"),
                        "source_path": d.get("source_path"),
                    }
                )
            if len(hits) >= limit:
                return

    await _scan("jcl_artifacts", "jcl_artifact")
    await _scan("cobol_artifacts", "cobol_artifact")
    await _scan("pli_artifacts", "pli_artifact")
    await _scan("copybook_artifacts", "copybook_artifact")
    await _scan("proc_artifacts", "proc_artifact")
    await _scan("sql_ddl_artifacts", "sql_ddl_artifact")
    return {"hits": hits[:limit], "total": len(hits[:limit])}


async def _diff_schema(
    table: str, dialect_a: str = "db2", dialect_b: str = "xdb"
) -> dict[str, Any]:
    if not table:
        raise ToolError("'table' is required", code="INVALID_ARGUMENT")
    cl = await _get_cloudant()
    a_docs = (
        await cl.find(
            "sql_ddl_artifacts",
            {
                "shop": DEMO_SHOP,
                "kind": "sql_ddl_artifact",
                "dialect": dialect_a,
                "table": table.upper(),
            },
            limit=1,
        )
    ).get("docs", [])
    b_docs = (
        await cl.find(
            "sql_ddl_artifacts",
            {
                "shop": DEMO_SHOP,
                "kind": "sql_ddl_artifact",
                "dialect": dialect_b,
                "table": table.upper(),
            },
            limit=1,
        )
    ).get("docs", [])
    if not a_docs or not b_docs:
        raise ToolError(
            f"both dialects must contain {table!r} (got a={bool(a_docs)} b={bool(b_docs)})",
            code="NOT_FOUND",
        )
    from app.services.mainframe_parser.sql_ddl import TableDef, diff_tables  # type: ignore

    a = TableDef.model_validate(a_docs[0]["parsed"])
    b = TableDef.model_validate(b_docs[0]["parsed"])
    diff = diff_tables(a, b)
    return diff.model_dump(mode="json")


async def _scenarios() -> dict[str, Any]:
    cl = await _get_cloudant()
    res = await cl.find("demo_scenarios", {"shop": DEMO_SHOP, "kind": "demo_scenario"}, limit=100)
    docs = sorted(res.get("docs", []), key=lambda d: d.get("scenario_id", ""))
    return {
        "scenarios": [
            {
                "scenario_id": d["scenario_id"],
                "title": d.get("title"),
                "summary": d.get("summary"),
                "source_region": d.get("source_region"),
                "target_region": d.get("target_region"),
                "expected_findings": d.get("expected_findings", []),
                "expected_score_trajectory": d.get("expected_score_trajectory", []),
            }
            for d in docs
        ],
        "total": len(docs),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


registry.register(
    "corpus_list_regions",
    description="List the 8 region names for the demo shop, with one-line descriptions.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)(_list_regions)


registry.register(
    "corpus_list_jcl",
    description="List JCL members; filter by region or source_pack.",
    input_schema={
        "type": "object",
        "properties": {
            "region": {"type": "string"},
            "source_pack": {"type": "string", "enum": ["bankdemo", "omp_course", "cobol_check"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 200},
        },
        "additionalProperties": False,
    },
)(_list_jcl)


registry.register(
    "corpus_get_jcl",
    description="Fetch one JCL artifact: source-blob hash, parsed AST, region.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "region": {"type": "string"},
        },
        "required": ["name"],
        "additionalProperties": False,
    },
)(_get_jcl)


registry.register(
    "corpus_get_copybook",
    description="Fetch every variant of a copybook (e.g. v1 vs v1-padded).",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "version": {"type": "string"},
        },
        "required": ["name"],
        "additionalProperties": False,
    },
)(_get_copybook)


registry.register(
    "corpus_search",
    description="Fuzzy substring search across JCL/COBOL/PL-I/copybook/proc/DDL.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 2},
            "kind": {
                "type": "string",
                "enum": [
                    "jcl_artifact",
                    "cobol_artifact",
                    "pli_artifact",
                    "copybook_artifact",
                    "proc_artifact",
                    "sql_ddl_artifact",
                ],
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
)(_search)


registry.register(
    "corpus_diff_schema",
    description="Diff a CREATE TABLE between two SQL dialects (db2 vs xdb).",
    input_schema={
        "type": "object",
        "properties": {
            "table": {"type": "string"},
            "dialect_a": {"type": "string", "enum": ["db2", "xdb"]},
            "dialect_b": {"type": "string", "enum": ["db2", "xdb"]},
        },
        "required": ["table"],
        "additionalProperties": False,
    },
)(_diff_schema)


registry.register(
    "corpus_scenarios",
    description="Return the five hero demo scenarios with expected score trajectories.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)(_scenarios)


def main() -> int:
    return run_cli(registry, sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
