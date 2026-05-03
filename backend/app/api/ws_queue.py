"""WebSocket route for the Review Queue — docs/API.md §13.

The full Cloudant `_changes` listener + per-user RBAC filter is Phase 1.5
(Bob worklist). For now, the WebSocket accepts authenticated connections,
sends the heartbeat, and echoes audit events the in-process broadcaster
publishes. This is enough surface for the frontend to integrate against and
for resilience tests to exercise reconnect-with-backoff.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.config import get_settings
from app.logging import get_logger
from app.services.auth import decode_token

router = APIRouter()
_log = get_logger("helios.ws")


class QueueBroadcaster:
    """In-process pub-sub for audit events.

    Bob will replace this with a Cloudant `_changes` consumer (Phase 1.5).
    The subscriber API stays the same; the broadcaster's ``publish`` is what
    changes shape.
    """

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[dict]] = []

    def subscribe(self) -> asyncio.Queue[dict]:
        q: asyncio.Queue[dict] = asyncio.Queue(maxsize=1000)
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict]) -> None:
        with contextlib.suppress(ValueError):
            self._queues.remove(q)

    async def publish(self, event: dict) -> None:
        for q in list(self._queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                _log.warning("ws.queue_full")


_broadcaster = QueueBroadcaster()


def get_broadcaster() -> QueueBroadcaster:
    return _broadcaster


@router.websocket("/ws/queue")
async def ws_queue(websocket: WebSocket, token: str = Query(...)) -> None:
    settings = get_settings()
    try:
        user = decode_token(token, settings)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="invalid token")
        return

    await websocket.accept()
    queue = _broadcaster.subscribe()
    heartbeat = asyncio.create_task(_heartbeat(websocket))
    seq = 0
    try:
        while True:
            event = await queue.get()
            seq += 1
            await websocket.send_text(
                json.dumps({"type": "audit_event", "seq": seq, "event": event})
            )
    except WebSocketDisconnect:
        _log.info("ws.disconnect", user=user.email)
    finally:
        heartbeat.cancel()
        _broadcaster.unsubscribe(queue)


async def _heartbeat(websocket: WebSocket) -> None:
    try:
        while True:
            await asyncio.sleep(25)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except (asyncio.CancelledError, WebSocketDisconnect):
        return
