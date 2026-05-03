"""Background job runner — queue interface + impls.

* In-memory impl: real, used in dev / tests.
* Cloudant impl: **STUB** (Bob, Phase 2 — durability for the audit bundle
  generator and other long jobs).
"""

from app.jobs.runner import JobRunner, JobState, JobRecord, get_job_runner

__all__ = ["JobRunner", "JobState", "JobRecord", "get_job_runner"]
