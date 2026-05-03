import { http, HttpResponse } from "msw";
import {
  ANIL,
  HERO_ABEND,
  HERO_ABEND_ANALYSIS,
  HERO_COBOL_SOURCE,
  HERO_DIFF,
  HERO_FINDINGS,
  HERO_JCL_SOURCE,
  HERO_QUEUE,
  HERO_SCORE_BREAKDOWN_100,
  HERO_SCORE_BREAKDOWN_62,
  HERO_SCORE_BREAKDOWN_94,
  HERO_SYSLOG_RAW,
  MAYA,
  REGIONS,
  REGION_PROFILES,
} from "./fixtures";

const API = "*";

function envelope<T>(data: T) {
  return HttpResponse.json({ ok: true, data, request_id: "req:mock" });
}

export const handlers = [
  // --- Health -----------------------------------------------------------
  http.get(`${API}/healthz`, () => envelope({ status: "ok" })),
  http.get(`${API}/version`, () =>
    envelope({
      version: "0.1.0-mock",
      git_sha: "mock",
      build_time: "now",
      image_tag: "mock",
    }),
  ),

  // --- Auth -------------------------------------------------------------
  http.post(`${API}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.password !== "helios2026") {
      return HttpResponse.json(
        {
          ok: false,
          error: { code: "UNAUTHORIZED", message: "Invalid email or password" },
          request_id: "req:mock",
        },
        { status: 401 },
      );
    }
    const user = body.email.startsWith("anil") ? ANIL : MAYA;
    return envelope({
      token: "mock-jwt",
      expires_at: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
      user,
    });
  }),
  http.post(`${API}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
  http.get(`${API}/auth/me`, () => envelope({ user: MAYA })),

  // --- Regions ----------------------------------------------------------
  http.get(`${API}/api/regions`, () => envelope({ regions: REGIONS, total: REGIONS.length })),
  http.get(`${API}/api/regions/:name`, ({ params }) => {
    const profile = REGION_PROFILES[params.name as string];
    return profile
      ? envelope(profile)
      : HttpResponse.json(
          {
            ok: false,
            error: {
              code: "REGION_NOT_FOUND",
              message: `No region named '${params.name}'`,
            },
            request_id: "req:mock",
          },
          { status: 404 },
        );
  }),
  http.post(`${API}/api/regions/:name`, ({ params }) =>
    envelope({
      name: params.name as string,
      audit_event_id: "audit:mock",
      review_required: false,
    }),
  ),
  // Hero-shot diff: the canonical 7 substitution-surface fields between
  // int2 and int3. For any other (a, b) combination return an empty diff
  // so the UI shows the "All fields aligned" path.
  http.get(`${API}/api/regions/:a/diff/:b`, ({ params }) => {
    const a = params.a as string;
    const b = params.b as string;
    const isHeroPair = (a === "int2" && b === "int3") || (a === "int3" && b === "int2");
    return envelope({
      a,
      b,
      fields: isHeroPair ? HERO_DIFF : [],
    });
  }),

  // --- JJSCAN+ ----------------------------------------------------------
  http.post(`${API}/api/scan`, () =>
    envelope({
      findings: HERO_FINDINGS,
      scan_duration_ms: 42,
    }),
  ),
  http.get(`${API}/api/scan/:id`, () =>
    envelope({
      job_id: "job:mock",
      state: "succeeded",
      jcl_name: "CUST_DELETE_INACTIVE",
      target_region: "int3",
      created_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      findings: HERO_FINDINGS,
    }),
  ),
  http.post(`${API}/api/scan/findings/:id/decide`, ({ params }) =>
    envelope({
      finding_id: params.id as string,
      state: "dismissed",
      decided_at: new Date().toISOString(),
      audit_event_id: "audit:mock-decide",
      learning_event_id: "learn:mock-decide",
    }),
  ),
  http.post(`${API}/api/scan/findings/:id/auto-fix`, ({ params }) =>
    envelope({
      finding_id: params.id as string,
      applied: true,
      diff: "// auto-fix applied (mock)",
    }),
  ),

  // --- Score ------------------------------------------------------------
  // Toggle the Maya trajectory off the request body: by default we return
  // the 62 score; when the request payload includes "applied_fixes" the
  // mock walks 62 → 94 → 100. The frontend confidence page can drive this
  // to demo the auto-fix flow without a backend.
  http.post(`${API}/api/score`, async ({ request }) => {
    let appliedFixes: string[] = [];
    try {
      const body = (await request.json()) as {
        applied_fixes?: string[];
      } | null;
      appliedFixes = body?.applied_fixes ?? [];
    } catch {
      // body might be a different shape — that's fine.
    }
    if (appliedFixes.length >= 2) {
      return envelope({ score: 100, breakdown: HERO_SCORE_BREAKDOWN_100 });
    }
    if (appliedFixes.includes("backup_gap")) {
      return envelope({ score: 94, breakdown: HERO_SCORE_BREAKDOWN_94 });
    }
    return envelope({ score: 62, breakdown: HERO_SCORE_BREAKDOWN_62 });
  }),
  http.get(`${API}/api/score/weights/:region`, ({ params }) =>
    envelope({
      region: params.region as string,
      weights: { critical: 25, high: 10, medium: 5, low: 2, info: 0 },
      source: "default",
    }),
  ),

  // --- Promote ----------------------------------------------------------
  http.post(`${API}/api/promote`, () =>
    envelope({
      promote_event_id: "audit:mock-promote",
      audit_event_id: "audit:mock-promote",
      diff: HERO_DIFF,
      confidence_score: 62,
      confidence_breakdown: {
        base: 100,
        "deduction.backup_gap": 30,
        "deduction.jjscan_high": 10,
        "boost.soft_rounding": 2,
      },
      auto_fixes_applied: [],
      auto_fixes_available_but_not_applied: [
        { fix: "generate_paired_backup", target: "PROD.INT3.CUST.MASTER" },
      ],
      state: "pending_review",
      reviewer: "required",
    }),
  ),

  // --- ABEND ------------------------------------------------------------
  http.post(`${API}/api/abend`, () => envelope(HERO_ABEND_ANALYSIS)),
  http.get(`${API}/api/abend/history`, () => envelope({ events: [HERO_ABEND] })),
  http.get(`${API}/api/abend/:id`, () =>
    envelope({
      ...HERO_ABEND_ANALYSIS,
      raw_text: HERO_SYSLOG_RAW,
      source_text: HERO_COBOL_SOURCE,
    }),
  ),
  http.post(`${API}/api/abend/:id/resolve`, ({ params }) =>
    envelope({
      event_id: params.id as string,
      audit_event_id: "audit:mock-resolve",
      learning_event_id: "learn:mock-resolve",
    }),
  ),

  // --- Queue ------------------------------------------------------------
  http.get(`${API}/api/queue`, () => envelope({ items: HERO_QUEUE })),
  http.post(`${API}/api/queue/:id/approve`, ({ params }) =>
    envelope({
      event_id: params.id as string,
      state: "approved",
      audit_event_id: "audit:mock-approve",
    }),
  ),
  http.post(`${API}/api/queue/:id/reject`, ({ params }) =>
    envelope({
      event_id: params.id as string,
      state: "rejected",
      audit_event_id: "audit:mock-reject",
    }),
  ),

  // --- Audit (paginated stub) -------------------------------------------
  http.get(`${API}/api/audit`, () =>
    envelope({
      items: [
        {
          id: "audit:mock:0001",
          type: "region_profile_edit",
          actor: MAYA.email,
          created_at: new Date().toISOString(),
          subject: { kind: "region", name: "int3" },
        },
      ],
      bookmark: null,
    }),
  ),

  // --- Runbooks ---------------------------------------------------------
  http.get(`${API}/api/runbooks`, () =>
    envelope({
      runbooks: [
        {
          id: "runbook:mock:s0c7-custproc",
          program: "CUSTPROC",
          abend_code: "S0C7",
          title: "S0C7 in CUSTPROC.CALC-INTEREST",
          updated_at: new Date().toISOString(),
        },
      ],
    }),
  ),

  // --- Sample JCL source for the Studio mock ----------------------------
  http.get(`${API}/api/jcl/CUST_DELETE_INACTIVE`, () =>
    envelope({ name: "CUST_DELETE_INACTIVE", source: HERO_JCL_SOURCE }),
  ),
];
