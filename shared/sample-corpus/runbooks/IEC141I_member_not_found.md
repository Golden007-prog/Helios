# Runbook: IEC141I 013-18 — PROC member not in target PROCLIB

## Symptom
`IEC141I 013-18,IGG0191A,...` with the failing PROC member named in the
SYSPRINT.

## Root cause
The PROC member referenced by the JCL was not promoted to the target
region's PROCLIB. Common after a partial promotion that copied the JCL but
not the PROC.

## Fix
Copy the missing member to the target PROCLIB:

```
//COPYPROC EXEC PGM=IEBCOPY
//SYSUT1   DD DSN=CUST.INT2.PROCLIB,DISP=SHR
//SYSUT2   DD DSN=CUST.INT3.PROCLIB,DISP=SHR
//SYSIN    DD *
   COPY OUTDD=SYSUT2,INDD=SYSUT1
   SELECT MEMBER=DBLOAD
```

## Verification
Re-run the job. No IEC141I.

## Prevention
JJSCAN+ rule `JJ-MISSING-PROC-MEMBER-001` detects this before promotion.
