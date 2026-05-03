"""Backup generator — emits paired backup JCL for protected resources.

Phase 1.3 deliverable. The selection logic + JCL templates are domain-specific
enough that they belong on Bob's worklist alongside the scoring engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackupRequest:
    protected_resource: str
    region_hlq: str
    job_name: str
    timestamp: datetime | None = None  # For deterministic testing


@dataclass
class BackupArtifact:
    backup_dataset_name: str
    jcl_text: str
    method: str  # "unload+image_copy" | "idcams_repro" | "pds_xmit"


def generate(request: BackupRequest, timestamp: datetime | None = None) -> BackupArtifact:
    """Generate paired backup JCL for the protected resource.

    Implements backup generation per docs/PHASE_PLAN.md §1.3:
    - VSAM datasets → IDCAMS REPRO
    - DB2 tables → UNLOAD + IMAGE COPY

    Backup DSN format: <region_hlq>.BAK.<resource_short>.D<yyjjj>.T<hhmmss>

    Args:
        request: Backup request with resource name and region HLQ
        timestamp: Optional timestamp for deterministic backup names (testing)
    """
    # Use provided timestamp or current time
    ts = timestamp or request.timestamp or datetime.utcnow()

    # Format timestamp components
    yyjjj = ts.strftime("%y%j")  # Year (2-digit) + Julian day
    hhmmss = ts.strftime("%H%M%S")  # Time

    # Extract resource short name (last component after dots)
    resource_parts = request.protected_resource.split(".")
    resource_short = resource_parts[-1] if resource_parts else request.protected_resource

    # Determine method based on resource name patterns
    # DB2 tables typically don't have dots or are in format SCHEMA.TABLE
    # VSAM datasets have multiple dots and often end with .PATH, .KSDS, etc.
    is_vsam = "." in request.protected_resource and any(
        request.protected_resource.upper().endswith(suffix)
        for suffix in [".PATH", ".PATH3", ".KSDS", ".ESDS", ".RRDS", ".CLUSTER"]
    )

    if is_vsam:
        # VSAM backup via IDCAMS REPRO
        method = "idcams_repro"
        backup_dsn = f"{request.region_hlq}.BAK.{resource_short}.D{yyjjj}.T{hhmmss}"

        jcl_text = f"""//BACKUP   JOB (HELIOS),'BACKUP {resource_short}',
//         CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//STEP1    EXEC PGM=IDCAMS,REGION=4M
//SYSPRINT DD   SYSOUT=*
//SYSIN    DD   *
  REPRO -
    INDATASET({request.protected_resource}) -
    OUTDATASET({backup_dsn}) -
    REPLACE
/*
//"""
    else:
        # DB2 table backup via UNLOAD + IMAGE COPY
        method = "unload+image_copy"
        backup_dsn = f"{request.region_hlq}.BAK.{resource_short}.D{yyjjj}.T{hhmmss}"

        jcl_text = f"""//BACKUP   JOB (HELIOS),'BACKUP {resource_short}',
//         CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//STEP1    EXEC PGM=DSNTIAUL
//STEPLIB  DD   DSN=DSN.V12R1M0.SDSNLOAD,DISP=SHR
//SYSPRINT DD   SYSOUT=*
//SYSUDUMP DD   SYSOUT=*
//SYSREC00 DD   DSN={backup_dsn}.UNLOAD,
//         DISP=(NEW,CATLG,DELETE),
//         SPACE=(CYL,(10,10),RLSE),
//         UNIT=SYSDA
//SYSPUNCH DD   DUMMY
//SYSIN    DD   *
  SELECT * FROM {request.protected_resource};
/*
//STEP2    EXEC PGM=DSNJU004
//STEPLIB  DD   DSN=DSN.V12R1M0.SDSNLOAD,DISP=SHR
//SYSPRINT DD   SYSOUT=*
//SYSUT1   DD   DSN={backup_dsn}.IMAGECOPY,
//         DISP=(NEW,CATLG,DELETE),
//         SPACE=(CYL,(50,50),RLSE),
//         UNIT=SYSDA
//SYSIN    DD   *
  COPY TABLESPACE DATABASE.{resource_short} -
    COPYDDN(SYSUT1) -
    FULL YES
/*
//"""

    return BackupArtifact(
        backup_dataset_name=backup_dsn,
        jcl_text=jcl_text,
        method=method,
    )
