"""Cloudant read-only MCP server.

Exposes the four operations Bob needs while planning Helios changes:

* ``list_collections``  — list helios_* databases
* ``get_document``      — read a single doc by id
* ``find_documents``    — Mango _find with selector + limit
* ``count_documents``   — count via Mango selector (paginated)

All tools are read-only. Writes go through the FastAPI backend so the audit
writer can hash-chain them. Bob is asked to confirm tool calls that don't
appear in alwaysAllow; the alwaysAllow list in .bob/mcp.json should match
the four names above and nothing else.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any
from urllib.parse import quote

import httpx

from _shared import ToolError, ToolRegistry, run_cli

CLOUDANT_URL = os.environ.get("CLOUDANT_URL", "")
CLOUDANT_APIKEY = os.environ.get("CLOUDANT_APIKEY", "")
CLOUDANT_DB_PREFIX = os.environ.get("CLOUDANT_DB_PREFIX", "helios_")
TIMEOUT_S = float(os.environ.get("CLOUDANT_TIMEOUT_SECONDS", "5"))
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# IAM token cache
_iam_token: str | None = None
_iam_expires_at: float = 0.0


registry = ToolRegistry(
    server_name="helios-cloudant",
    description="Read-only Cloudant queries scoped to helios_* collections.",
)


async def _get_iam_token() -> str:
    """Get or refresh IBM Cloud IAM token."""
    global _iam_token, _iam_expires_at

    if not CLOUDANT_APIKEY:
        raise ToolError("CLOUDANT_APIKEY is not set", code="CONFIG_MISSING")

    # Return cached token if still valid (with 60s buffer)
    if _iam_token and time.time() < _iam_expires_at - 60:
        return _iam_token

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            IAM_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": CLOUDANT_APIKEY,
            },
        )
        if resp.status_code >= 400:
            raise ToolError(
                f"IAM token exchange failed ({resp.status_code})",
                code="IAM_EXCHANGE_FAILED",
            )
        data = resp.json()
        _iam_token = str(data["access_token"])
        _iam_expires_at = time.time() + int(data.get("expires_in", 3600))
        assert _iam_token is not None
        return _iam_token


async def _client() -> httpx.AsyncClient:
    if not CLOUDANT_URL:
        raise ToolError(
            "CLOUDANT_URL must be set in the environment",
            code="CONFIG_MISSING",
        )
    token = await _get_iam_token()
    return httpx.AsyncClient(
        base_url=CLOUDANT_URL.rstrip("/"),
        timeout=TIMEOUT_S,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )


def _scope(short: str) -> str:
    """Reject any non-prefixed name; return the full database name."""
    if "/" in short or short.startswith("_"):
        raise ToolError(f"Invalid database name {short!r}", code="INVALID_DB")
    if short.startswith(CLOUDANT_DB_PREFIX):
        full = short
    else:
        full = f"{CLOUDANT_DB_PREFIX}{short}"
    if not full.startswith(CLOUDANT_DB_PREFIX):
        raise ToolError(f"Out-of-scope database {full!r}", code="OUT_OF_SCOPE")
    return full


@registry.register(
    "list_collections",
    description="Return every helios_* database visible on the Cloudant instance.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)
async def list_collections() -> dict[str, Any]:
    async with await _client() as http:
        resp = await http.get("/_all_dbs")
        resp.raise_for_status()
        all_dbs = resp.json()
    helios = [d for d in all_dbs if d.startswith(CLOUDANT_DB_PREFIX)]
    return {"collections": sorted(helios), "total": len(helios), "prefix": CLOUDANT_DB_PREFIX}


@registry.register(
    "get_document",
    description="Fetch one document from a helios_* collection by id.",
    input_schema={
        "type": "object",
        "properties": {
            "collection": {"type": "string", "description": "short name (e.g. 'regions')"},
            "doc_id": {"type": "string"},
        },
        "required": ["collection", "doc_id"],
        "additionalProperties": False,
    },
)
async def get_document(collection: str, doc_id: str) -> dict[str, Any]:
    db = _scope(collection)
    async with await _client() as http:
        resp = await http.get(f"/{quote(db, safe='')}/{quote(doc_id, safe='')}")
        if resp.status_code == 404:
            return {"found": False, "collection": db, "doc_id": doc_id}
        resp.raise_for_status()
        return {"found": True, "collection": db, "document": resp.json()}


@registry.register(
    "find_documents",
    description="Run a Mango _find against a helios_* collection.",
    input_schema={
        "type": "object",
        "properties": {
            "collection": {"type": "string"},
            "selector": {"type": "object"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 25},
            "fields": {"type": "array", "items": {"type": "string"}},
            "sort": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["collection", "selector"],
        "additionalProperties": False,
    },
)
async def find_documents(
    collection: str,
    selector: dict[str, Any],
    limit: int = 25,
    fields: list[str] | None = None,
    sort: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    db = _scope(collection)
    body: dict[str, Any] = {"selector": selector, "limit": min(max(limit, 1), 200)}
    if fields:
        body["fields"] = fields
    if sort:
        body["sort"] = sort
    async with await _client() as http:
        resp = await http.post(f"/{quote(db, safe='')}/_find", json=body)
        resp.raise_for_status()
        data = resp.json()
    return {
        "collection": db,
        "documents": data.get("docs", []),
        "bookmark": data.get("bookmark"),
        "warning": data.get("warning"),
    }


@registry.register(
    "count_documents",
    description="Count documents matching a Mango selector (walks bookmarks).",
    input_schema={
        "type": "object",
        "properties": {
            "collection": {"type": "string"},
            "selector": {"type": "object"},
        },
        "required": ["collection", "selector"],
        "additionalProperties": False,
    },
)
async def count_documents(collection: str, selector: dict[str, Any]) -> dict[str, Any]:
    db = _scope(collection)
    total = 0
    bookmark: str | None = None
    async with await _client() as http:
        while True:
            body = {"selector": selector, "limit": 200, "fields": ["_id"]}
            if bookmark:
                body["bookmark"] = bookmark
            resp = await http.post(f"/{quote(db, safe='')}/_find", json=body)
            resp.raise_for_status()
            data = resp.json()
            docs = data.get("docs", [])
            total += len(docs)
            new_bookmark = data.get("bookmark")
            if not docs or not new_bookmark or new_bookmark == bookmark:
                break
            bookmark = new_bookmark
    return {"collection": db, "total": total}


def main() -> int:
    return run_cli(registry, sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
