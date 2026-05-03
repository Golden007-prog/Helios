"""Idempotently apply every Cloudant index in cloudant_indexes.json.

Usage:
    python -m migrations.apply_indexes               # apply
    python -m migrations.apply_indexes --rollback    # delete all design docs

Reads credentials from the same .env the backend uses. Skips silently if the
backend is in in-memory Cloudant mode (no credentials).

Authenticates with IBM Cloud IAM (matches ``backend/app/services/cloudant.py``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import get_settings

INDEX_FILE = Path(__file__).parent / "cloudant_indexes.json"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


class _IamClient:
    def __init__(self, apikey: str, timeout: float) -> None:
        self._apikey = apikey
        self._timeout = timeout
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._http = httpx.AsyncClient(timeout=timeout)

    async def token(self, *, force_refresh: bool = False) -> str:
        if not force_refresh and self._token and time.time() < self._expires_at - 60:
            return self._token
        resp = await self._http.post(
            IAM_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self._apikey,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600))
        assert self._token is not None
        return self._token

    async def close(self) -> None:
        await self._http.aclose()


async def _ensure_db(http: httpx.AsyncClient, iam: _IamClient, name: str) -> None:
    token = await iam.token()
    resp = await http.put(
        f"/{quote(name, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code in (201, 202, 412):
        return
    resp.raise_for_status()


async def _create_index(http: httpx.AsyncClient, iam: _IamClient, db: str, index: dict) -> str:
    token = await iam.token()
    resp = await http.post(
        f"/{quote(db, safe='')}/_index",
        json=index,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("result", "exists")


async def _list_design_docs(http: httpx.AsyncClient, iam: _IamClient, db: str) -> list[str]:
    token = await iam.token()
    resp = await http.get(
        f"/{quote(db, safe='')}/_design_docs",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    rows = resp.json().get("rows", [])
    return [r["id"] for r in rows if r["id"].startswith("_design/")]


async def _delete_design_doc(http: httpx.AsyncClient, iam: _IamClient, db: str, ddoc: str) -> bool:
    token = await iam.token()
    head = await http.get(
        f"/{quote(db, safe='')}/{quote(ddoc, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if head.status_code != 200:
        return False
    rev = head.json()["_rev"]
    resp = await http.delete(
        f"/{quote(db, safe='')}/{quote(ddoc, safe='')}",
        params={"rev": rev},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.status_code in (200, 202)


async def _apply(payload: dict) -> int:
    settings = get_settings()
    if not (settings.cloudant_url and settings.cloudant_apikey):
        print("Cloudant credentials missing — apply_indexes is a no-op.")
        return 0

    iam = _IamClient(settings.cloudant_apikey, timeout=settings.cloudant_timeout_seconds)
    try:
        async with httpx.AsyncClient(
            base_url=str(settings.cloudant_url).rstrip("/"),
            timeout=15.0,
            headers={"Accept": "application/json"},
        ) as http:
            seen: set[str] = set()
            for entry in payload["indexes"]:
                short = entry["db"]
                full = (
                    short
                    if short.startswith(settings.cloudant_db_prefix)
                    else f"{settings.cloudant_db_prefix}{short}"
                )
                if full not in seen:
                    await _ensure_db(http, iam, full)
                    seen.add(full)
                    print(f"db ok        {full}")

                result = await _create_index(http, iam, full, entry["index"])
                print(f"index {result:<8s} {full} :: {entry['index']['name']}")
    finally:
        await iam.close()
    return 0


async def _rollback(payload: dict) -> int:
    settings = get_settings()
    if not (settings.cloudant_url and settings.cloudant_apikey):
        print("Cloudant credentials missing — rollback is a no-op.")
        return 0

    iam = _IamClient(settings.cloudant_apikey, timeout=settings.cloudant_timeout_seconds)
    try:
        async with httpx.AsyncClient(
            base_url=str(settings.cloudant_url).rstrip("/"),
            timeout=15.0,
            headers={"Accept": "application/json"},
        ) as http:
            dbs = sorted(
                {
                    (
                        entry["db"]
                        if entry["db"].startswith(settings.cloudant_db_prefix)
                        else f"{settings.cloudant_db_prefix}{entry['db']}"
                    )
                    for entry in payload["indexes"]
                }
            )
            for db in dbs:
                ddocs = await _list_design_docs(http, iam, db)
                for ddoc in ddocs:
                    deleted = await _delete_design_doc(http, iam, db, ddoc)
                    print(f"ddoc {('deleted' if deleted else 'kept   '):<8s} {db} :: {ddoc}")
    finally:
        await iam.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Cloudant index migrations.")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Delete every Mango design doc owned by the migration (does not delete data).",
    )
    args = parser.parse_args()

    payload = json.loads(INDEX_FILE.read_text())
    if args.rollback:
        return asyncio.run(_rollback(payload))
    return asyncio.run(_apply(payload))


if __name__ == "__main__":
    sys.exit(main())
