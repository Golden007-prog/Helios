// Maya/MeridianBank fixtures consumed by every MSW handler. Mirrors the
// backend seed in backend/migrations/seed_demo.py so demo + mock-mode
// behavior stay aligned.

import type {
  AbendEvent,
  Finding,
  QueueItem,
  RegionListItem,
  RegionProfile,
  User,
} from "@/lib/api/types";

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
      confidence_weight_overrides:
        r.name === "int3" ? { critical_multiplier: 150 } : {},
    },
  ]),
);

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
    description:
      "CUSTREC resolves to v3 in PROD.INT2.SYSLIB but v4 in PROD.INT3.SYSLIB.",
    details: { copybook: "CUSTREC", source_version: "v3", target_version: "v4" },
    auto_fix_available: true,
    decision: "pending",
    created_at: new Date().toISOString(),
  },
  {
    id: "find:demo:db2-plan",
    rule_id: "JJ-DB2-PLAN-MISMATCH-001",
    severity: "critical",
    description:
      "DSN SYSTEM(DB2I) PLAN(INT2.COLL) does not match int3 (DB2I / INT3.COLL).",
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
      score: 94,
    },
  },
];
