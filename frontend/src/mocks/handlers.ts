import { http, HttpResponse } from "msw";
import {
  ANIL,
  HERO_ABEND,
  HERO_FINDINGS,
  HERO_JCL_SOURCE,
  HERO_QUEUE,
  MAYA,
  REGIONS,
  REGION_PROFILES,
} from "./fixtures";

const API = "*";

function envelope<T>(data: T) {
  return HttpResponse.json({ ok: true, data, request_id: "req:mock" });
}

function bobStub(message: string) {
  return HttpResponse.json(
    {
      ok: false,
      error: {
        code: "NOT_IMPLEMENTED",
        message: `BOB: ${message}`,
        details: { reserved_for: "Bob" },
      },
      request_id: "req:mock",
    },
    { status: 501 },
  );
}

export const handlers = [
  // --- Health
  http.get(`${API}/healthz`, () => envelope({ status: "ok" })),
  http.get(`${API}/version`, () =>
    envelope({ version: "0.1.0-mock", git_sha: "mock", build_time: "now", image_tag: "mock" }),
  ),

  // --- Auth
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

  // --- Regions
  http.get(`${API}/api/regions`, () => envelope({ regions: REGIONS, total: REGIONS.length })),
  http.get(`${API}/api/regions/:name`, ({ params }) => {
    const profile = REGION_PROFILES[params.name as string];
    return profile
      ? envelope(profile)
      : HttpResponse.json(
          {
            ok: false,
            error: { code: "REGION_NOT_FOUND", message: `No region named '${params.name}'` },
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
  http.get(`${API}/api/regions/:a/diff/:b`, () =>
    bobStub("region diff renderer + algorithm reserved for Bob (docs/PHASE_PLAN.md §1.2)"),
  ),

  // --- JJSCAN+
  http.post(`${API}/api/scan`, () =>
    bobStub("JJSCAN+ analyzer core reserved for Bob (docs/PHASE_PLAN.md §1.3)"),
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

  // --- Score
  http.post(`${API}/api/score`, () =>
    bobStub("Confidence Score formula reserved for Bob (docs/CONFIDENCE_SCORE.md)"),
  ),

  // --- Promote
  http.post(`${API}/api/promote`, () =>
    bobStub("Promote depends on score + diff — both reserved for Bob"),
  ),

  // --- ABEND
  http.post(`${API}/api/abend`, () =>
    bobStub("ABEND classifier inference pipeline reserved for Bob (docs/PHASE_PLAN.md §1.4)"),
  ),
  http.get(`${API}/api/abend/history`, () => envelope({ events: [HERO_ABEND] })),
  http.get(`${API}/api/abend/:id`, () => envelope(HERO_ABEND)),

  // --- Queue
  http.get(`${API}/api/queue`, () => envelope({ items: HERO_QUEUE })),

  // --- Audit (paginated stub)
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

  // --- Runbooks
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

  // --- Sample JCL source for the Studio mock
  http.get(`${API}/api/jcl/CUST_DELETE_INACTIVE`, () =>
    envelope({ name: "CUST_DELETE_INACTIVE", source: HERO_JCL_SOURCE }),
  ),
];
