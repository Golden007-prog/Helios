/**
 * Real BankDemo content baked into the bundle for the demo flow.
 *
 * Source: ``test dataset/helios_sample_dataset/01_BankDemo/`` (Rocket
 * BankDemo). These strings are committed verbatim so reviewers can hit
 * "Run scan" / "Analyze" on the deployed Pages site and see findings on
 * authentic mainframe artifacts rather than synthetic placeholders.
 *
 * For larger artifacts (full ZBNKBAT1, full BBANK40P COBOL) we keep the
 * essential excerpt. Anything more than ~5 KB blows up the bundle for
 * marginal demo value — the four hero JCLs all fit easily.
 */

export interface JclSample {
  name: string;
  description: string;
  source: string;
}

export const BANKDEMO_JCLS: JclSample[] = [
  {
    name: "ZBNKDEL.jcl",
    description:
      "Hero scenario — DELETE BNKACC.PATH3 (triggers backup_gap penalty + copybook drift in target region)",
    source: `//BACPATH  JOB MFIDEMO,MFIDEMO,CLASS=A,MSGCLASS=A
//*
//* DELETE path
//*
//STEP2     EXEC PGM=IDCAMS,REGION=512K
//SYSPRINT  DD   SYSOUT=A
//SYSIN     DD   *
         DELETE  -
           MFI01V.MFIDEMO.BNKACC.PATH3 -
           PATH PURGE
//
`,
  },
  {
    name: "ZBNKBAT1.jcl",
    description:
      "Batch extract — fires all four JJSCAN+ rules when promoted to bnk_pac (PROC missing, plan mismatch, copybook drift, override conflict)",
    source: `//MFIDEMO  JOB MFIDEMO,MFIDEMO,CLASS=1,MSGCLASS=O,NOTIFY=MFIDEMO
//* ZBNKBAT1.JCL — extract + sort + print
//EXTRACT  EXEC YBATTSO
//TSO.SYSTSIN DD *
 DSN SYSTEM(DB10)
     RUN PROGRAM(ZBNKEXT1) +
         PLAN(MYPLAN) +
         LIB('MFI01.MFIDEMO.LOADLIB') +
         PARMS('ALL')
 END
//EXTRACT  DD DSN=MFI01.MFIDEMO.BANKEXT1(+1),DISP=(NEW,CATLG,DELETE),
//            DCB=(RECFM=VB,LRECL=99,BLKSIZE=990),
//            UNIT=SYSDA,SPACE=(TRK,(2,1),RLSE)
//SORT     EXEC PGM=SORT
//EXITLIB  DD DSN=MFI01.MFIDEMO.LOADLIB,DISP=SHR
//SYSOUT   DD SYSOUT=*
//SORTIN   DD DSN=MFI01.MFIDEMO.BANKEXT1(+1),DISP=SHR
//SORTOUT  DD DSN=MFI01.MFIDEMO.BANKSRT1(+1),DISP=(NEW,CATLG,DELETE),
//            DCB=(RECFM=VB,LRECL=99,BLKSIZE=990),
//            UNIT=SYSDA,SPACE=(TRK,(2,1),RLSE)
//SYSIN    DD DSN=MFI01.MFIDEMO.CTLCARDS(KBNKSRT1),DISP=SHR
//PRINT    EXEC YBNKPRT1,GEN='+1',PRM='HELLO WORLD'
`,
  },
  {
    name: "ZBNKEXT1.jcl",
    description: "Extract job — single-step batch with DB2 plan binding",
    source: `//ZBNKEXT1 JOB MFIDEMO,MFIDEMO,CLASS=A,MSGCLASS=A,NOTIFY=&SYSUID
//*
//STEP1    EXEC PGM=IKJEFT01
//STEPLIB  DD DSN=MFI01.MFIDEMO.LOADLIB,DISP=SHR
//SYSPRINT DD SYSOUT=*
//SYSTSPRT DD SYSOUT=*
//SYSTSIN  DD *
 DSN SYSTEM(DB10)
     RUN PROGRAM(ZBNKEXT1) PLAN(MFIDEMO_T)
 END
//EXTRACT  DD DSN=MFI01.MFIDEMO.BANKEXT1,DISP=SHR
//
`,
  },
  {
    name: "ZBNKINT1.jcl",
    description: "Interest calculation — runs over BNKACC, PROC chain to YBNKPRT1",
    source: `//ZBNKINT1 JOB MFIDEMO,MFIDEMO,CLASS=A,MSGCLASS=A
//*
//* Interest calculation pass
//*
//CALC     EXEC PGM=IKJEFT01,DYNAMNBR=20
//STEPLIB  DD DSN=MFI01.MFIDEMO.LOADLIB,DISP=SHR
//SYSPRINT DD SYSOUT=*
//SYSTSPRT DD SYSOUT=*
//SYSTSIN  DD *
 DSN SYSTEM(DB10)
     RUN PROGRAM(BBANK40P) PLAN(MFIDEMO_T) PARMS('CALC-INTEREST')
 END
//PRINT    EXEC YBNKPRT1,PRM='INT-REPORT'
//
`,
  },
];

export interface AbendSample {
  name: string;
  description: string;
  program: string;
  raw_text: string;
}

export const BANKDEMO_ABENDS: AbendSample[] = [
  {
    name: "S0C7 in BBANK40P",
    description:
      "Subscript out of range — BANK-SCREEN30-INPUT(-1) when BNKTXN returns no rows. Hero ABEND scenario from PERSONA_MAYA Scene 2.",
    program: "BBANK40P",
    raw_text: `JES2 JOB LOG -- SYSTEM MERIDIAN -- NODE PRD01
09.14.22 JOB22189 ---- THURSDAY, 14 MAY 2026 ----
09.14.22 JOB22189 IRR010I  USERID BNKDEV01 IS ASSIGNED TO THIS JOB.
09.14.22 JOB22189 $HASP373 BBANK40P STARTED - INIT 04 - CLASS T - SYS DEV01
09.14.22 JOB22189 IEF403I BBANK40P - STARTED - TIME=09.14.22
09.14.27 JOB22189 +CEE3204S THE SYSTEM DETECTED A PROTECTION EXCEPTION (SYSTEM COMPLETION CODE=0C7).
09.14.27 JOB22189 *** CEEDUMP FOLLOWS ***
                  CEE3DMP V2 R5 M0: Dump processed at 2026/05/14 09:14:27
                  PSW=078D2400 80003D78
                  ABEND CODE 0C7 - DATA EXCEPTION
                  Failing instruction at offset +0x000003D8 in BBANK40P
                  Compile unit BBANK40P
                  Source statement at line 287
                  Paragraph: POPULATE-TXN-LIST

                  IGZ0035S The reference to table BANK-SCREEN30-INPUT (subscript = -1)
                          attempted to use a subscript value not within the
                          permitted range (1..30).

                  SYMBOLIC TRACE:
                    BANK-SCREEN30-INPUT(-1)
                      ← indexed by WS-SUB1 at line 287
                    WS-SUB1
                      ← decremented in COMPUTE WS-SUB1 = WS-SUB1 - 1 at line 282
                    initial WS-SUB1
                      ← MOVE BANK-TXN-COUNT TO WS-SUB1 at line 271
                    BANK-TXN-COUNT
                      ← READ from BNKTXN VSAM cluster at line 198
                      (returned ZERO rows for the requested account)

09.14.27 JOB22189 IEF450I BBANK40P GO - ABEND=S0C7 U0000 REASON=00000000
09.14.27 JOB22189 $HASP395 BBANK40P ENDED - RC=ABEND
`,
  },
  {
    name: "IEC141I 013-18 in proclib",
    description: "Member not found — promote forgot to copy the PROC to target PROCLIB",
    program: "ZBNKBAT1",
    raw_text: `JES2 JOB LOG
$HASP373 ZBNKBAT1 STARTED - INIT 02 - CLASS A
IEF236I ALLOC. FOR ZBNKBAT1 EXTRACT
IEC141I 013-18,IFG0194B,ZBNKBAT1,EXTRACT,JCL00001,,,
        SYS1.PROCLIB(YBATTSO)
IEF272I ZBNKBAT1 EXTRACT - STEP WAS NOT EXECUTED.
IEF142I ZBNKBAT1 EXTRACT - STEP WAS NOT RUN BECAUSE OF CONDITION CODES
$HASP395 ZBNKBAT1 ENDED - RC=08
`,
  },
  {
    name: "SQLCODE -805 in DBANK01P",
    description: "Plan not bound — promoted to a region whose collection lacks the package",
    program: "DBANK01P",
    raw_text: `JES2 JOB LOG
$HASP373 ZBNKINT1 STARTED - INIT 04 - CLASS T
DSNT408I SQLCODE = -805, ERROR:  DBRM OR PACKAGE NAME
         MFIDEMO_T.DBANK01P.18A2C001A2C001A2 NOT FOUND IN PLAN MFIDEMO_T.
DSNT415I SQLERRP   = DSNXOSC SQL PROCEDURE DETECTING ERROR
DSNT416I SQLERRD   = -250 0 0 -1 0 0 SQL DIAGNOSTIC INFORMATION
IEF142I ZBNKINT1 CALC - STEP WAS NOT RUN BECAUSE OF CONDITION CODES
$HASP395 ZBNKINT1 ENDED - RC=12
`,
  },
];

/** A short safe identifier suitable for Pages URL routing — used by MSW
 * to mint job/event ids that match a pre-rendered route. Same shape as
 * the IDs in ``frontend/src/app/{jjscan,abend}/[id]/page.tsx`` static
 * params. */
export function safeId(prefix: string): string {
  // Avoid colons (Windows static export can't write filenames with ``:``)
  // and any other URL-unsafe chars.
  return `${prefix}-${Date.now().toString(36)}`;
}
