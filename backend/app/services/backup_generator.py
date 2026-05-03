"""Backup generator — emits paired backup JCL for protected resources.

Phase 1.3 deliverable. The selection logic + JCL templates are domain-specific
enough that they belong on Bob's worklist alongside the scoring engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackupRequest:
    protected_resource: str
    region_hlq: str
    job_name: str


@dataclass
class BackupArtifact:
    backup_dataset_name: str
    jcl_text: str
    method: str  # "unload+image_copy" | "idcams_repro" | "pds_xmit"


def generate(request: BackupRequest) -> BackupArtifact:
    """Generate paired backup JCL for the protected resource.

    BOB: implement per docs/PHASE_PLAN.md §1.3 and docs/CONFIDENCE_SCORE.md
    "Backup gap" component.

    * UNLOAD + IMAGE COPY for DB2 protected tables.
    * IDCAMS REPRO for VSAM datasets.
    * Returns deterministic backup dataset name based on date + GDG pattern.
    """
    raise NotImplementedError(
        "BOB: implement backup generator (docs/PHASE_PLAN.md §1.3)"
    )
