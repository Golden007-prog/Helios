"""HTTP route registration.

Each feature module exposes a single ``router``. Importing this package is
side-effect-free; routes only attach when :func:`register_routes` is called.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import (
    abend,
    audit,
    auth,
    health,
    jcl,
    jjscan,
    learning,
    promote,
    queue,
    regions,
    runbooks,
    score,
    ws_queue,
)


def register_routes(app: FastAPI) -> None:
    # Health probes are unprefixed and unauthed.
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])

    api_groups = [
        (regions.router, "/api/regions", "regions"),
        (jcl.router, "/api/jcl", "jcl"),
        (promote.router, "/api/promote", "promote"),
        (jjscan.router, "/api/scan", "jjscan"),
        (score.router, "/api/score", "score"),
        (abend.router, "/api/abend", "abend"),
        (runbooks.router, "/api/runbooks", "runbooks"),
        (audit.router, "/api/audit", "audit"),
        (learning.router, "/api/learning", "learning"),
        (queue.router, "/api/queue", "queue"),
    ]
    for router, prefix, tag in api_groups:
        app.include_router(router, prefix=prefix, tags=[tag])

    # WebSocket route — no prefix so it lives under /ws/queue.
    app.include_router(ws_queue.router)
