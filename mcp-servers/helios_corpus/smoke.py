"""End-to-end smoke for the helios-corpus MCP server.

Bootstraps the Cloudant in-memory client, runs the corpus seeder, then
invokes each registered tool once and asserts a non-empty response.

Usage:
    python -m helios_corpus.smoke
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Force in-memory Cloudant before any backend imports.
os.environ.setdefault("CLOUDANT_URL", "")
os.environ.setdefault("CLOUDANT_APIKEY", "")
os.environ.setdefault("WATSONX_APIKEY", "")
os.environ.setdefault("WATSONX_PROJECT_ID", "")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-ship-32chars000")


async def _run() -> int:
    from app.config import get_settings
    from app.services.cloudant import CloudantClient
    from migrations.seed_corpus import seed_all

    cl = CloudantClient(get_settings())
    report = await seed_all(cl)
    print(
        f"seeded: regions={report.regions} jcl={report.jcl} cobol={report.cobol} "
        f"pli={report.pli} ddl={report.ddl_tables} cpy={report.copybooks} "
        f"procs={report.procs} fixtures={report.fixtures} scenarios={report.scenarios}"
    )

    # Reuse the same client across tools to avoid creating a second
    # in-memory store. The server uses a module-global lazy client; we
    # plug ours in.
    from helios_corpus import server

    server._client = cl  # type: ignore[attr-defined]

    results: dict[str, Any] = {}

    results["corpus_list_regions"] = await server._list_regions()
    assert results["corpus_list_regions"]["total"] == 8, results["corpus_list_regions"]

    results["corpus_list_jcl"] = await server._list_jcl(region="bnk_test_vsam")
    assert results["corpus_list_jcl"]["total"] > 0

    results["corpus_get_jcl"] = await server._get_jcl(name="ZBNKDEL", region="bnk_test_vsam")
    assert results["corpus_get_jcl"]["parsed"]["steps"]

    results["corpus_get_copybook"] = await server._get_copybook(name="COPY001")
    assert results["corpus_get_copybook"]["total"] >= 1

    results["corpus_search"] = await server._search(query="MFI01.MFIDEMO", limit=10)
    assert results["corpus_search"]["total"] > 0

    results["corpus_diff_schema"] = await server._diff_schema(
        table="BNKACC", dialect_a="db2", dialect_b="xdb"
    )
    assert results["corpus_diff_schema"]["table"] == "BNKACC"

    results["corpus_scenarios"] = await server._scenarios()
    assert results["corpus_scenarios"]["total"] == 5

    print(json.dumps({k: _trim(v) for k, v in results.items()}, indent=2, default=str))
    await cl.close()
    return 0


def _trim(value: Any) -> Any:
    """Truncate large values so the smoke output stays readable."""
    if isinstance(value, dict):
        return {
            k: _trim(v) for k, v in value.items() if k not in {"raw_text", "parsed", "dump_text"}
        }
    if isinstance(value, list):
        return [_trim(v) for v in value[:5]]
    if isinstance(value, str) and len(value) > 200:
        return value[:200] + "…"
    return value


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
