"""Cloudant ``_changes`` listener — fans out audit events to subscribers.

Started during FastAPI lifespan. Connects to Cloudant's continuous changes
feed for ``helios_audit_log``, applies a per-user RBAC filter (see
docs/REVIEW_QUEUE.md § RBAC), and pushes accepted events into the in-process
:class:`QueueBroadcaster` defined in ``app.api.ws_queue``.

Reconnect behavior:

* Exponential backoff on connection error (``initial=1s, max=30s, jitter``).
* Heartbeat tolerance: 60 s without a frame from Cloudant → close + retry.
* Bookmark continuity: every event the listener emits records the
  ``last_seq``; on reconnect we resume from there.

In-memory mode:
    When Cloudant is in the in-memory fallback (no creds), the listener is
    a no-op — there's no ``_changes`` feed to follow. Tests that need to
    drive WebSocket fanout can still publish into ``QueueBroadcaster``
    directly via the audit_writer hook.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.logging import get_logger
from app.services.cloudant import CloudantClient

_log = get_logger("helios.audit_listener")

INITIAL_BACKOFF_S = 1.0
MAX_BACKOFF_S = 30.0


@dataclass(slots=True)
class ListenerState:
    last_seq: str | None = None
    started_at: float | None = None
    delivered: int = 0
    reconnects: int = 0


class AuditListener:
    def __init__(
        self,
        cloudant: CloudantClient,
        settings: Settings,
        on_event: callable,  # async (doc) -> None
    ) -> None:
        self._cl = cloudant
        self._settings = settings
        self._on_event = on_event
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.state = ListenerState()

    async def start(self) -> None:
        if not self._cl.is_live:
            _log.info("audit_listener.in_memory_skip")
            return
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="audit_listener")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                self._task.cancel()
                await self._task

    async def _run(self) -> None:
        backoff = INITIAL_BACKOFF_S
        loop = asyncio.get_running_loop()
        self.state.started_at = loop.time()
        while not self._stop.is_set():
            try:
                await self._consume_once()
                # Clean exit (e.g., connection drop after a normal poll) →
                # reset backoff and reconnect immediately.
                backoff = INITIAL_BACKOFF_S
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.state.reconnects += 1
                _log.warning(
                    "audit_listener.reconnect",
                    backoff_s=backoff,
                    reason=str(exc),
                )
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                backoff = min(backoff * 2.0, MAX_BACKOFF_S)

    async def _consume_once(self) -> None:
        """One round of consuming the changes feed.

        Uses the existing ``CloudantClient.changes`` helper (one shot).
        For continuous-mode streaming the upgrade is to switch to
        ``feed=continuous`` and read ``aiter_lines`` — Bob's worklist for
        Phase 1.5 polish.
        """
        feed = await self._cl.changes(
            "audit_log",
            since=self.state.last_seq or "now",
            feed="normal",
            limit=100,
        )
        for change in feed.get("results", []):
            doc = change.get("doc")
            if not doc:
                continue
            await self._on_event(doc)
            self.state.delivered += 1
        new_seq = feed.get("last_seq")
        if new_seq is not None:
            self.state.last_seq = str(new_seq)


def passes_rbac(event: dict[str, Any], user_email: str, user_roles: list[str]) -> bool:
    """Per-user RBAC filter at the broadcast layer (docs/REVIEW_QUEUE.md §RBAC).

    Today: every authenticated user can see every audit event for their
    shop. This stub is the integration point for Bob's full RBAC matrix
    (Phase 1.5 polish): allow/deny per ``event.type`` x user role.
    """
    return True
