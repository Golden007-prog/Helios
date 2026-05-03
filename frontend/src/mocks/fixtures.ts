// Maya/MeridianBank fixtures consumed by every MSW handler. Mirrors the
// backend seed in backend/migrations/seed_demo.py so demo + mock-mode
// behavior stay aligned.

import type {
  AbendEvent,
  DiffField,
  Finding,
  QueueItem,
  RegionListItem,
  RegionProfile,
  User,
} from "@/lib/api/types";
import type { AbendAnalysisResponse } from "@/features/abend/types";
import type { ServerScoreBreakdown } from "@/lib/api/score";

export const MAYA: User = {
  user_id: "user:maya@meridianbank.demo:01HXYDEMO00000000000MAYA0",
  email: "maya@meridianbank.demo",
  display_name: "Maya Patel",
  roles: ["developer"],
  shop: "meridianbank",
};

export const ANIL: User = {
  user_id: "user:anil@meridianbank.demo:01HXYDEMO00000000000ANIL0",
  email: "anil@meridianbank.demo",
  display_name: "Anil Verma",
  roles: ["reviewer", "developer"],
  shop: "meridianbank",
};

export const REGIONS: RegionListItem[] = [
  { name: "sandbox", tier: "sandbox", hlq: "PROD.SAND" },
  { name: "dev1", tier: "development", hlq: "PROD.DEV1" },
  { name: "dev2", tier: "development", hlq: "PROD.DEV2" },
  { name: "int2", tier: "integration", hlq: "PROD.INT2" },
  { name: "int3", tier: "integration", hlq: "PROD.INT3" },
  { name: "prod", tier: "production", hlq: "PROD.PROD" },
  { name: "dr", tier: "production", hlq: "PROD.DR" },
];

export const REGION_PROFILES: Record<string, RegionProfile> = Object.fromEntries(
  REGIONS.map((r) => [
    r.name,
    {
      name: r.name,
      tier: r.tier,
      hlq: r.hlq,
      db2: { subsystem_id: "DB2P", plan_collection: `${r.name.toUpperCase()}.COLL` },
      racf_group: "BANKAPP",
      scheduler_queue: r.name === "int3" ? "DAILY-INT3" : "DAILY",
      volser_pattern: r.name === "int3" ? "VS3*" : "VS*",
      protected_resources: r.name === "int3" ? ["PROD.INT3.CUST.MASTER"] : [],
      confidence_weight_overrides: {} as Record<string, number>,
    },
  ]),
);

// 7-field substitution-surface diff for the int2 → int3 demo arc, matching
// the backend's diff_regions output.
export const HERO_DIFF: DiffField[] = [
  { path: "tier", a: "integration", b: "integration", kind: "value_change" },
  { path: "hlq", a: "PROD.INT2", b: "PROD.INT3", kind: "value_change" },
  {
    path: "db2.subsystem_id",
    a: "DB2I",
    b: "DB2I",
    kind: "value_change",
  },
  {
    path: "db2.plan_collection",
    a: "INT2.COLL",
    b: "INT3.COLL",
    kind: "value_change",
  },
  { path: "racf_group", a: "INT2DEV", b: "INT3DEV", kind: "value_change" },
  { path: "jes.class_", a: "A", b: "P", kind: "value_change" },
  {
    path: "scheduler_queue",
    a: "DAILY",
    b: "DAILY-INT3",
    kind: "value_change",
  },
];

export const HERO_JCL_SOURCE = `//CUSTDELI JOB (BANK,APP),'MAYA P',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//* Hero JCL — promotes int2 → int3 in the demo arc.
//STEP010  EXEC PGM=IKJEFT01,DYNAMNBR=20
//STEPLIB  DD DSN=PROD.INT2.LOAD,DISP=SHR
//SYSPRINT DD SYSOUT=*
//SYSTSPRT DD SYSOUT=*
//SYSTSIN  DD *
   DSN SYSTEM(DB2I)
   RUN PROGRAM(CUSTDEL) PLAN(INT2.COLL)
   END
//STEP020  EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
   DELETE PROD.INT2.CUST.MASTER NONVSAM
`;

export const HERO_FINDINGS: Finding[] = [
  {
    id: "find:demo:copybook-drift",
    rule_id: "JJ-COPYBOOK-DRIFT-001",
    severity: "medium",
    description: "CUSTREC resolves to v3 in PROD.INT2.SYSLIB but v4 in PROD.INT3.SYSLIB.",
    details: { copybook: "CUSTREC", source_version: "v3", target_version: "v4" },
    auto_fix_available: true,
    decision: "pending",
    created_at: new Date().toISOString(),
  },
  {
    id: "find:demo:db2-plan",
    rule_id: "JJ-DB2-PLAN-MISMATCH-001",
    severity: "critical",
    description: "DSN SYSTEM(DB2I) PLAN(INT2.COLL) does not match int3 (DB2I / INT3.COLL).",
    details: { in_jcl: "INT2.COLL", expected: "INT3.COLL" },
    auto_fix_available: true,
    decision: "pending",
    created_at: new Date().toISOString(),
  },
  {
    id: "find:demo:backup-gap",
    rule_id: "BACKUP-GAP-001",
    severity: "high",
    description:
      "PROD.INT3.CUST.MASTER is a protected resource but no IDCAMS REPRO precedes the DELETE.",
    details: {},
    auto_fix_available: true,
    decision: "pending",
    created_at: new Date().toISOString(),
  },
];

export const HERO_ABEND: AbendEvent = {
  event_id: "abend:demo:0001",
  abend_code: "S0C7",
  program: "CUSTPROC",
  tier: "confirmed",
  created_at: new Date().toISOString(),
  summary:
    "Data exception in CALC-INTEREST when CUST-RATE-PCT contains spaces. Likely root cause: SELECT did not filter dropped rows.",
};

export const HERO_QUEUE: QueueItem[] = [
  {
    event_id: "queue:demo:0001",
    state: "pending_review",
    type: "promote_request",
    initiator: "maya@meridianbank.demo",
    reviewers: ["anil@meridianbank.demo"],
    created_at: new Date().toISOString(),
    payload: {
      jcl: "CUST_DELETE_INACTIVE",
      target_region: "int3",
      score: 62,
      top_reasons: ["Backup gap (-30)", "Copybook drift (-10)", "JES class T → P (-3)"],
    },
  },
];

// Rich score breakdown matching the Maya 62 → 94 → 100 trajectory.
export const HERO_SCORE_BREAKDOWN_62: ServerScoreBreakdown = {
  base: 100,
  deductions: { backup_gap: 30, jjscan_high: 10 },
  boosts: { soft_rounding: 2 },
};

export const HERO_SCORE_BREAKDOWN_94: ServerScoreBreakdown = {
  base: 100,
  deductions: { jjscan_high: 10 },
  boosts: { soft_rounding: 4 },
};

export const HERO_SCORE_BREAKDOWN_100: ServerScoreBreakdown = {
  base: 100,
  deductions: {},
  boosts: {},
};

// Full ABEND analysis envelope for the seeded S0C7 dump.
export const HERO_ABEND_ANALYSIS: AbendAnalysisResponse = {
  pattern_code: "S0C7",
  identified_abend: { code: "S0C7", confidence: 0.92, tier: "confirmed" },
  failing_step: {
    program: "CUSTPROC",
    step_name: "STEP010",
    offset_hex: "1A4",
  },
  source_trace: {
    paragraph: "2300-CALC-RETIREMENT",
    highlighted_field: "WS-DOB",
    line: 247,
    file: "CUSTPROC.cbl",
  },
  business_rule_explanation:
    "S0C7 data exception: numeric op on non-numeric WS-DOB. Most likely cause is uninitialised field; READ from CUST.MASTER returned NULL.",
  ranked_root_causes: [
    {
      cause: "Uninitialised WS-DOB before MOVE",
      prior_count: 45,
      confidence: 0.92,
    },
    {
      cause: "Bad input record with non-numeric DOB",
      prior_count: 30,
      confidence: 0.78,
    },
    {
      cause: "DISPLAY value used where COMP-3 expected",
      prior_count: 18,
      confidence: 0.66,
    },
  ],
  matching_runbooks: [
    {
      id: "rb-cobol-s0c7-handling",
      title: "S0C7 Data Exception Troubleshooting",
      success_count: 127,
    },
  ],
  degraded: false,
  quarantine_sql: "DELETE FROM CUST WHERE DOB IS NULL;",
};

// Raw SYSLOG fragment + COBOL source for the three-pane mock view.
export const HERO_SYSLOG_RAW = `JES2 JOB LOG -- SYSTEM MERIDIAN -- NODE PRD01
14.32.04 JOB12345 IEF403I CUSTPROC - STARTED - TIME=14.32.04
14.32.08 JOB12345 +CEE3204S THE SYSTEM DETECTED A PROTECTION EXCEPTION (CC=0C7).
                  CEE3DMP V2 R5 M0: Dump processed at 2026/10/14 14:32:08
                  ABEND CODE 0C7 - DATA EXCEPTION
                  Failing instruction at offset +0x1A4 in CUSTPROC
                  Compile unit CUSTPROC
                                          Statement: 247
                                          Paragraph: 2300-CALC-RETIREMENT
                  STORAGE DUMP (around failing field WS-DOB):
                  +0x000  WS-CUST-DOB-INT      = 40404040 (display NULL)
                  +0x008  WS-CUST-AGE          = -- (uninitialized)
14.32.08 JOB12345 IEF450I CUSTPROC GO - ABEND=S0C7
14.32.08 JOB12345 $HASP395 CUSTPROC ENDED - RC=ABEND`;

export const HERO_COBOL_SOURCE = `       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTPROC.
       PROCEDURE DIVISION.
       0500-READ-INPUT.
           READ CUSTREC.
       1000-PROCESS-RECORD.
           MOVE CUSTREC-DOB TO WS-DOB.
       2300-CALC-RETIREMENT.
           COMPUTE WS-CUST-AGE = WS-DOB - 1900.`;
