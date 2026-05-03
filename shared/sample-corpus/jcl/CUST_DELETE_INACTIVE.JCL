//CUSTDELI JOB (BANK,APP),'MAYA P',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//*  Hero JCL — promotes int2 → int3 in the demo arc.
//*  Seeded defects (Maya's Scene 1):
//*    1. Copybook drift: SYSLIB chain in int3 still pins CUSTREC v2.7
//*       while int2 source uses v3.1. Detected by JJSCAN+
//*       JJ-COPYBOOK-DRIFT-001.
//*    2. Missing backup pair: int3.protected_resources lists CUST.MASTER
//*       and this job has no UNLOAD/IMAGE COPY step. Confidence Score
//*       deducts 30. Auto-fix generates the paired backup job.
//*    3. (Indirect) Historical: 3 prior incidents on similar
//*       DELETE_INACTIVE patterns in this region in the last 30 days.
//STEP010  EXEC PGM=IKJEFT01,DYNAMNBR=20
//STEPLIB  DD DSN=CUST.INT2.LOAD,DISP=SHR
//SYSLIB   DD DSN=CUST.INT2.COPYLIB,DISP=SHR
//         DD DSN=CUST.SHARED.COPYLIB,DISP=SHR
//SYSPRINT DD SYSOUT=*
//SYSTSPRT DD SYSOUT=*
//SYSTSIN  DD *
   DSN SYSTEM(DBI2)
   RUN PROGRAM(CUSTDEL) PLAN(CUSTPKG.INT2) PARMS('AGE_THRESHOLD=2555')
   END
//STEP020  EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
   DELETE CUST.INT2.CUST.INACTIVE NONVSAM
