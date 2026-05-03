"""Background job runner — in-memory implementation, Cloudant-backed stub.

The in-memory runner is real: routes can submit jobs, query status, cancel,
and consume results. It uses ``asyncio.create_task`` and is appropriate for
single-instance dev / hackathon demo. The Cloudant-backed durable runner
(survives restarts, supports replay) is a Bob stub for Phase 2.

Public surface — the only thing dependencies.py imports:

* :class:`JobRunner`
* :class:`JobState`
* :class:`JobRecord`
* :func:`get_job_runner` — process-wide singleton
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache
from typing import Any

import ulid

from app.errors import BobStubError, ErrorCode, HeliosError
from app.logging import get_logger

_log = get_logger("helios.jobs")

JobHandler = Callable[["JobRecord"], Awaitable[Any]]


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobRecord:
    job_id: str
    kind: str
    payload: dict[str, Any]
    state: JobState = JobState.PENDING
    created_at: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    progress: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "progress": self.progress,
            "error": self.error,
        }


class JobRunner:
    """In-memory async job runner."""

    def __init__(self) -> None:
        self._records: dict[str, JobRecord] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._handlers: dict[str, JobHandler] = {}

    def register(self, kind: str, handler: JobHandler) -> None:
        if kind in self._handlers:
            raise ValueError(f"Job kind {kind!r} already registered")
        self._handlers[kind] = handler

    def submit(self, kind: str, payload: dict[str, Any]) -> JobRecord:
        if kind not in self._handlers:
            raise HeliosError(
                ErrorCode.INVALID_PAYLOAD, f"No handler registered for job kind {kind!r}"
            )
        rec = JobRecord(
            job_id=f"job:{ulid.new().str}",
            kind=kind,
            payload=payload,
            created_at=_now(),
        )
        self._records[rec.job_id] = rec
        self._tasks[rec.job_id] = asyncio.create_task(self._run(rec))
        _log.info("job.submitted", job_id=rec.job_id, kind=kind)
        return rec

    def get(self, job_id: str) -> JobRecord | None:
        return self._records.get(job_id)

    def list(
        self, *, kind: str | None = None, state: JobState | None = None, limit: int = 50
    ) -> list[JobRecord]:
        out: list[JobRecord] = []
        for rec in reversed(list(self._records.values())):
            if kind and rec.kind != kind:
                continue
            if state and rec.state != state:
                continue
            out.append(rec)
            if len(out) >= limit:
                break
        return out

    async def cancel(self, job_id: str) -> JobRecord:
        rec = self._records.get(job_id)
        if rec is None:
            raise HeliosError(ErrorCode.EVENT_NOT_FOUND, f"No job {job_id!r}")
        if rec.state in (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED):
            return rec
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        rec.state = JobState.CANCELLED
        rec.finished_at = _now()
        return rec

    async def wait(self, job_id: str, timeout: float | None = None) -> JobRecord:
        task = self._tasks.get(job_id)
        if task is not None:
            with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        rec = self._records.get(job_id)
        if rec is None:
            raise HeliosError(ErrorCode.EVENT_NOT_FOUND, f"No job {job_id!r}")
        return rec

    async def _run(self, rec: JobRecord) -> None:
        handler = self._handlers[rec.kind]
        rec.state = JobState.RUNNING
        rec.started_at = _now()
        try:
            rec.result = await handler(rec)
            rec.state = JobState.SUCCEEDED
        except asyncio.CancelledError:
            rec.state = JobState.CANCELLED
            raise
        except Exception as exc:
            rec.state = JobState.FAILED
            rec.error = str(exc)
            _log.error("job.failed", job_id=rec.job_id, kind=rec.kind, error=str(exc))
        finally:
            rec.finished_at = _now()


class CloudantJobRunner(JobRunner):
    """Durable job runner backed by Cloudant.

    BOB: implement when Phase 2 needs survivable jobs (audit bundle generator,
    long-running watsonx batch). Spec lives in docs/RUNBOOK.md once written.
    """

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise BobStubError(
            "Cloudant-backed durable job runner is reserved for Bob",
            feature="jobs.CloudantJobRunner",
            spec_doc="docs/RUNBOOK.md (Phase 2)",
        )


@lru_cache(maxsize=1)
def get_job_runner() -> JobRunner:
    """Process-wide singleton."""
    return JobRunner()


def reset_job_runner() -> None:
    """Tests use this between cases."""
    get_job_runner.cache_clear()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
