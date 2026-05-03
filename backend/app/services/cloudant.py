"""Cloudant client wrapper.

Thin async client over the Cloudant HTTP API with IAM bearer authentication,
retry, scoping helpers (`db("audit_log")` -> `helios_audit_log`), typed
``get/put/find`` helpers, and an ``in_memory_for_tests`` mode that lets the
backend run end-to-end without Cloudant credentials.

Auth flow: an IBM Cloud IAM access token is fetched from
``https://iam.cloud.ibm.com/identity/token`` using
``grant_type=urn:ibm:params:oauth:grant-type:apikey``, cached until 60s
before its ``expires_in`` value, and refreshed on demand or on a 401 from
Cloudant. Every Cloudant request carries ``Authorization: Bearer <token>``.

The full data model lives in docs/DATA_MODEL.md. Indexes are declared in
``backend/migrations/cloudant_indexes.json`` and applied by
``apply_indexes.py``.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from copy import deepcopy
from typing import Any
from urllib.parse import quote

import httpx
import ulid
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import Settings
from app.errors import ErrorCode, HeliosError
from app.logging import get_logger

_log = get_logger("helios.cloudant")

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


class CloudantError(HeliosError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.CLOUDANT_UPSTREAM, message, details=details)


class _RetryableHTTPError(Exception):
    """5xx and 429 — let tenacity retry these. 4xx others are not retried."""


class CloudantClient:
    """Async Cloudant client.

    When ``settings.enable_cloudant`` is False **or** credentials are missing,
    the client falls back to an in-memory dict-of-dicts so tests, MCP smoke
    runs, and local dev without Cloudant credentials can still exercise the
    full HTTP surface.
    """

    def __init__(self, settings: Settings, *, http: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._prefix = settings.cloudant_db_prefix
        self._timeout = settings.cloudant_timeout_seconds
        self._max_retries = settings.cloudant_max_retries

        # IAM token cache.
        self._iam_token: str | None = None
        self._iam_expires_at: float = 0.0

        # Decide live vs. in-memory.
        creds_present = bool(settings.cloudant_url and settings.cloudant_apikey)
        self._live = settings.enable_cloudant and creds_present

        if self._live:
            assert settings.cloudant_url is not None
            assert settings.cloudant_apikey is not None
            # Cloudant calls share one client; IAM exchange runs through the
            # same client (relative URL preserved via ``base_url``) but with
            # the absolute IAM URL passed explicitly.
            self._http = http or httpx.AsyncClient(
                base_url=str(settings.cloudant_url).rstrip("/"),
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
            # Separate, untargeted client for IAM so the base_url doesn't
            # interfere when constructing the absolute IAM URL.
            self._iam_http = http or httpx.AsyncClient(timeout=self._timeout)
        else:
            self._http = None
            self._iam_http = None
            # In-memory store: {db_name -> {doc_id -> doc}}.
            self._memory: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
            _log.info("cloudant.in_memory_mode", reason="missing_creds_or_disabled")

    # --- Naming helpers ------------------------------------------------------

    def db_name(self, short: str) -> str:
        """Return the fully-prefixed Cloudant DB name (`audit_log` -> `helios_audit_log`)."""
        return short if short.startswith(self._prefix) else f"{self._prefix}{short}"

    @property
    def is_live(self) -> bool:
        return self._live

    # --- Lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        for h in (self._http, self._iam_http):
            if h is not None:
                await h.aclose()

    async def ping(self) -> tuple[bool, str | None]:
        """Used by /readyz. Returns (ok, detail)."""
        if not self._live:
            return True, "in-memory mode"
        try:
            data = await self._request("GET", "/")
            return True, data.get("version") if isinstance(data, dict) else None
        except Exception as exc:
            return False, str(exc)

    # --- IAM token --------------------------------------------------------

    async def _iam_token_value(self, *, force_refresh: bool = False) -> str:
        """Return a valid IBM Cloud IAM token. Refresh 60 s before expiry.

        ``force_refresh=True`` skips the cache and is what the 401-retry path
        passes when a request comes back with ``Unauthorized``.
        """
        if not self._live:
            raise CloudantError("Cloudant is in in-memory mode; no IAM exchange")
        if not force_refresh and self._iam_token and time.time() < self._iam_expires_at - 60:
            return self._iam_token
        assert self._iam_http is not None
        resp = await self._iam_http.post(
            IAM_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self._settings.cloudant_apikey or "",
            },
        )
        if resp.status_code >= 400:
            raise CloudantError(
                "IAM token exchange failed",
                details={"status": resp.status_code, "body": resp.text[:500]},
            )
        data = resp.json()
        self._iam_token = data["access_token"]
        self._iam_expires_at = time.time() + int(data.get("expires_in", 3600))
        assert self._iam_token is not None
        return self._iam_token

    # --- Low-level HTTP with retry ------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if not self._live:
            raise RuntimeError("CloudantClient._request called in in-memory mode")

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential_jitter(initial=0.3, max=4.0, jitter=0.5),
            retry=retry_if_exception_type(_RetryableHTTPError),
            reraise=True,
        ):
            with attempt:
                resp = await self._do_request(method, path, json_body=json_body, params=params)
                # 401 → refresh once and retry the same request before bubbling up.
                if resp.status_code == 401:
                    resp = await self._do_request(
                        method, path, json_body=json_body, params=params, force_refresh=True
                    )
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise _RetryableHTTPError(f"{resp.status_code} {resp.text[:200]}")
                if resp.status_code >= 400:
                    raise CloudantError(
                        f"Cloudant {method} {path} -> {resp.status_code}",
                        details={"status": resp.status_code, "body": resp.text[:500]},
                    )
                if not resp.content:
                    return {}
                return resp.json()

        raise CloudantError("Cloudant request exhausted retries (unreachable)")

    async def _do_request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any,
        params: dict[str, Any] | None,
        force_refresh: bool = False,
    ) -> httpx.Response:
        token = await self._iam_token_value(force_refresh=force_refresh)
        assert self._http is not None
        return await self._http.request(
            method,
            path,
            json=json_body,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

    # --- Database management ------------------------------------------------

    async def ensure_database(self, short: str) -> None:
        """Create the database if missing. Idempotent."""
        name = self.db_name(short)
        if not self._live:
            self._memory.setdefault(name, {})
            return
        try:
            await self._request("PUT", f"/{quote(name, safe='')}")
        except CloudantError as exc:
            # 412 = already exists; that's success.
            if exc.details.get("status") == 412:
                return
            raise

    async def list_databases(self) -> list[str]:
        if not self._live:
            return sorted(self._memory.keys())
        result = await self._request("GET", "/_all_dbs")
        return [d for d in result if d.startswith(self._prefix)]

    # --- Document CRUD ------------------------------------------------------

    async def get(self, short: str, doc_id: str) -> dict[str, Any] | None:
        name = self.db_name(short)
        if not self._live:
            doc = self._memory.get(name, {}).get(doc_id)
            return deepcopy(doc) if doc else None
        try:
            return await self._request("GET", f"/{quote(name, safe='')}/{quote(doc_id, safe='')}")
        except CloudantError as exc:
            if exc.details.get("status") == 404:
                return None
            raise

    async def put(
        self,
        short: str,
        doc: dict[str, Any],
        *,
        doc_id: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a document. Returns the doc (with `_id`/`_rev`)."""
        name = self.db_name(short)
        doc = deepcopy(doc)
        if doc_id is not None:
            doc["_id"] = doc_id
        if "_id" not in doc:
            doc["_id"] = f"doc:{ulid.new().str}"

        if not self._live:
            self._memory.setdefault(name, {})
            existing = self._memory[name].get(doc["_id"])
            new_rev = f"{(int(existing['_rev'].split('-')[0]) + 1) if existing else 1}-mem"
            doc["_rev"] = new_rev
            self._memory[name][doc["_id"]] = deepcopy(doc)
            return deepcopy(doc)

        result = await self._request(
            "PUT",
            f"/{quote(name, safe='')}/{quote(doc['_id'], safe='')}",
            json_body=doc,
        )
        doc["_rev"] = result.get("rev", doc.get("_rev"))
        return doc

    async def delete(self, short: str, doc_id: str, rev: str) -> None:
        name = self.db_name(short)
        if not self._live:
            self._memory.get(name, {}).pop(doc_id, None)
            return
        await self._request(
            "DELETE",
            f"/{quote(name, safe='')}/{quote(doc_id, safe='')}",
            params={"rev": rev},
        )

    # --- Mango query --------------------------------------------------------

    async def find(
        self,
        short: str,
        selector: dict[str, Any],
        *,
        limit: int = 25,
        sort: list[dict[str, str]] | None = None,
        fields: list[str] | None = None,
        bookmark: str | None = None,
    ) -> dict[str, Any]:
        """Mango ``_find``. Returns the raw response (`docs`, `bookmark`)."""
        name = self.db_name(short)
        if not self._live:
            docs = [
                deepcopy(d)
                for d in self._memory.get(name, {}).values()
                if _matches_selector(d, selector)
            ]
            return {"docs": docs[:limit], "bookmark": None}

        body: dict[str, Any] = {"selector": selector, "limit": limit}
        if sort:
            body["sort"] = sort
        if fields:
            body["fields"] = fields
        if bookmark:
            body["bookmark"] = bookmark
        return await self._request(
            "POST",
            f"/{quote(name, safe='')}/_find",
            json_body=body,
        )

    async def count(self, short: str, selector: dict[str, Any]) -> int:
        result = await self.find(short, selector, limit=1, fields=["_id"])
        # Cloudant Mango doesn't return a total — for an exact count, fall back
        # to walking the bookmark in chunks. For the hackathon corpus (≪1k
        # docs/collection) the pagination is fine.
        if not self._live:
            return len(result["docs"])
        total = len(result["docs"])
        bookmark = result.get("bookmark")
        while result["docs"] and bookmark:
            result = await self.find(short, selector, limit=200, bookmark=bookmark, fields=["_id"])
            total += len(result["docs"])
            new_bookmark = result.get("bookmark")
            if new_bookmark == bookmark:
                break
            bookmark = new_bookmark
        return total

    # --- Bulk + helpers -----------------------------------------------------

    async def bulk_docs(self, short: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        name = self.db_name(short)
        if not self._live:
            results: list[dict[str, Any]] = []
            for doc in docs:
                stored = await self.put(short, doc)
                results.append({"id": stored["_id"], "rev": stored["_rev"], "ok": True})
            return results
        return await self._request(
            "POST",
            f"/{quote(name, safe='')}/_bulk_docs",
            json_body={"docs": docs},
        )

    async def changes(
        self,
        short: str,
        *,
        since: str | int = "now",
        feed: str = "normal",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Read the `_changes` feed.

        Used by the Review Queue audit listener (Phase 1.5). For continuous
        streaming see :meth:`stream_changes` in the future Bob impl — this
        helper covers the polling-fallback case.
        """
        name = self.db_name(short)
        if not self._live:
            # In-memory: produce a synthetic snapshot for the Review Queue
            # polling fallback to consume. Includes the doc so the audit
            # listener and the polling fallback both work uniformly.
            store = self._memory.get(name, {})
            return {
                "results": [
                    {
                        "seq": f"{i}-mem",
                        "id": doc_id,
                        "changes": [{"rev": d.get("_rev")}],
                        "doc": deepcopy(d),
                    }
                    for i, (doc_id, d) in enumerate(store.items())
                ],
                "last_seq": f"{len(store)}-mem",
                "pending": 0,
            }
        params: dict[str, Any] = {"since": since, "feed": feed, "include_docs": "true"}
        if limit is not None:
            params["limit"] = limit
        return await self._request("GET", f"/{quote(name, safe='')}/_changes", params=params)

    # --- Test helpers -------------------------------------------------------

    def in_memory_dump(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return a deep copy of the in-memory store. In-memory mode only."""
        if self._live:
            raise RuntimeError("in_memory_dump called on live Cloudant client")
        return deepcopy(self._memory)

    def in_memory_clear(self) -> None:
        if self._live:
            raise RuntimeError("in_memory_clear called on live Cloudant client")
        self._memory.clear()


def _matches_selector(doc: dict[str, Any], selector: dict[str, Any]) -> bool:
    """Tiny Mango-selector matcher for the in-memory mode.

    Supports equality, ``$eq``, ``$in``, ``$gt/$gte/$lt/$lte``, dotted paths,
    and top-level ``$and`` / ``$or``. This is intentionally a small subset —
    enough for the seeded queries the backend issues. The live path delegates
    to Cloudant's full Mango engine.
    """
    if "$and" in selector:
        return all(_matches_selector(doc, sub) for sub in selector["$and"])
    if "$or" in selector:
        return any(_matches_selector(doc, sub) for sub in selector["$or"])

    for path, expected in selector.items():
        actual = _resolve_path(doc, path)
        if isinstance(expected, dict):
            for op, value in expected.items():
                if op == "$eq" and actual != value:
                    return False
                if op == "$ne" and actual == value:
                    return False
                if op == "$in" and actual not in value:
                    return False
                if op == "$gt" and not (actual is not None and actual > value):
                    return False
                if op == "$gte" and not (actual is not None and actual >= value):
                    return False
                if op == "$lt" and not (actual is not None and actual < value):
                    return False
                if op == "$lte" and not (actual is not None and actual <= value):
                    return False
                if op == "$exists" and (actual is not None) != bool(value):
                    return False
        else:
            if actual != expected:
                return False
    return True


def _resolve_path(doc: dict[str, Any], path: str) -> Any:
    if "." not in path:
        return doc.get(path)
    cur: Any = doc
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def dump_doc(doc: dict[str, Any]) -> str:
    """Compact canonical JSON — used by the audit writer's chain hash."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))
