"""Audit writer — writes hash-chained events to ``helios_audit_log``.

Per docs/AUDIT_LOG.md: every state-changing endpoint MUST call
:meth:`AuditWriter.write_event`. The lint rule ``tools/lint_audit_calls.py``
enforces this in CI.

This module owns the *plumbing*: canonicalization (RFC 8785 / JCS-style via
``app.utils.canonical_json``), chain hash computation, and the Cloudant
write. It does not own *what to log* — that's the caller's responsibility
per the catalogue in docs/AUDIT_LOG.md.

Genesis marker:
    The first event in the chain has ``chain.prev_event_hash = "GENESIS"``
    and ``chain.prev_event_id = None``. This matches the algorithm in
    ``docs/audit_writer_plan.md`` §3 and is what the chain verifier expects
    when walking from the root.

The chain validator (`audit_chain_verify` job) and the daily attestation
generator are separate modules — this writer provides the per-event hash and
the pointer to the previous event, which is what they consume.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import ulid

from app.config import Settings
from app.errors import ErrorCode, HeliosError
from app.logging import get_logger
from app.services.cloudant import CloudantClient
from app.utils.canonical_json import canonicalize_bytes

_log = get_logger("helios.audit")

GENESIS = "GENESIS"


def canonical_json(obj: Any) -> bytes:
    """Backwards-compatible alias for the canonical_json utility."""
    return canonicalize_bytes(obj)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_event_hash(event: Mapping[str, Any]) -> str:
    """Return the SHA-256 of ``event``'s canonical JSON, excluding ``chain.this_event_hash``.

    Public so the chain verifier and attestation job can recompute hashes
    without rebuilding the writer's internal state.
    """
    hashable = {k: v for k, v in event.items() if k != "_rev"}
    chain = dict(hashable.get("chain", {}))
    chain.pop("this_event_hash", None)
    hashable["chain"] = chain
    return sha256_hex(canonicalize_bytes(hashable))


class AuditError(HeliosError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.INTERNAL, message, details=details)


class AuditWriter:
    """Append-only writer for ``helios_audit_log``.

    Concurrency: a single in-process lock serializes chain reads + writes.
    Cross-process serialization is not required for the hackathon (single
    Code Engine instance); the chain validator detects any out-of-order
    writes that slip through.
    """

    DB_SHORT = "audit_log"

    def __init__(self, cloudant: CloudantClient, settings: Settings) -> None:
        self._cl = cloudant
        self._settings = settings
        self._lock = asyncio.Lock()
        self._tail: tuple[str, str] | None = None  # (event_id, this_event_hash)
        self._db_ensured = False

    async def _ensure(self) -> None:
        if not self._db_ensured:
            await self._cl.ensure_database(self.DB_SHORT)
            self._db_ensured = True

    async def write_event(
        self,
        *,
        type: str,
        actor: str,
        actor_role: str,
        subject: Mapping[str, Any],
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
        result: str = "success",
        error: str | None = None,
        client_meta: Mapping[str, Any] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one event. Returns the persisted event document.

        ``before`` / ``after`` are arbitrary JSON-serializable structures —
        only their SHA-256s are stored on the event itself; the full payloads
        are reserved for an optional blob store wired up in Phase 2.
        """
        await self._ensure()
        async with self._lock:
            now = datetime.now(timezone.utc)
            event_id = (
                f"evt:{now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z:{type}:{ulid.new().str}"
            )

            prev_id, prev_hash = await self._latest_chain_tip()

            event: dict[str, Any] = {
                "_id": event_id,
                "schema_version": "1.0",
                "kind": "audit_event",
                "shop": self._settings.shop,
                "type": type,
                "actor": actor,
                "actor_role": actor_role,
                "ts": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "ts_unix_ms": int(now.timestamp() * 1000),
                "subject": dict(subject),
                "before_sha256": sha256_hex(canonical_json(before)) if before is not None else None,
                "after_sha256": sha256_hex(canonical_json(after)) if after is not None else None,
                "result": result,
                "client_meta": dict(client_meta) if client_meta else {},
                "chain": {
                    # Genesis marker for the first event; the previous event's
                    # hash for every subsequent event. ``prev_event_id`` is
                    # None for genesis so the chain verifier can detect it.
                    "prev_event_id": prev_id,
                    "prev_event_hash": prev_hash if prev_hash is not None else GENESIS,
                    "this_event_hash": None,  # filled in below
                },
            }
            if error:
                event["error"] = error
            if extra:
                event["extra"] = dict(extra)

            event_hash = compute_event_hash(event)
            event["chain"]["this_event_hash"] = event_hash

            try:
                stored = await self._cl.put(self.DB_SHORT, event)
            except HeliosError:
                _log.error("audit.write_failed", type=type, subject=dict(subject))
                raise

            self._tail = (event_id, event_hash)
            _log.info(
                "audit.event",
                type=type,
                actor=actor,
                subject_kind=event["subject"].get("kind"),
                subject_name=event["subject"].get("name"),
                result=result,
            )
            return stored

    async def latest(self) -> dict[str, Any] | None:
        """Return the most recent audit event, or None if the log is empty."""
        result = await self._cl.find(
            self.DB_SHORT,
            {"shop": self._settings.shop, "kind": "audit_event"},
            limit=1,
            sort=[{"ts_unix_ms": "desc"}],
        )
        docs = result.get("docs", [])
        return docs[0] if docs else None

    async def query(
        self,
        *,
        subject_kind: str | None = None,
        subject_name: str | None = None,
        actor: str | None = None,
        type: str | None = None,
        since_ms: int | None = None,
        until_ms: int | None = None,
        limit: int = 100,
        bookmark: str | None = None,
    ) -> dict[str, Any]:
        """Run an ``_find`` against the audit log with the common filters."""
        await self._ensure()
        sel: dict[str, Any] = {"shop": self._settings.shop, "kind": "audit_event"}
        if subject_kind:
            sel["subject.kind"] = subject_kind
        if subject_name:
            sel["subject.name"] = subject_name
        if actor:
            sel["actor"] = actor
        if type:
            sel["type"] = type
        if since_ms is not None or until_ms is not None:
            range_op: dict[str, Any] = {}
            if since_ms is not None:
                range_op["$gte"] = since_ms
            if until_ms is not None:
                range_op["$lte"] = until_ms
            sel["ts_unix_ms"] = range_op
        return await self._cl.find(
            self.DB_SHORT,
            sel,
            limit=limit,
            sort=[{"ts_unix_ms": "asc"}],
            bookmark=bookmark,
        )

    async def _latest_chain_tip(self) -> tuple[str | None, str | None]:
        if self._tail is not None:
            return self._tail
        last = await self.latest()
        if not last:
            return None, None
        return last["_id"], last.get("chain", {}).get("this_event_hash")
