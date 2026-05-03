// AUTO-GENERATED — do not edit by hand.
// Source: shared/constants/*.json via shared/codegen/dump_constants.py

export const BANNED_WATSONX_MODELS = {
  "$comment": "Banned watsonx models \u2014 single source of truth. Backend imports this list via app.config.BANNED_WATSONX_MODELS and asserts at every inference. Frontend never sends model ids, but uses this to render the model selector with these greyed out.",
  "banned": [
    "llama-3-405b-instruct",
    "mistral-medium-2505",
    "mistral-small-3-1-24b-instruct-2503"
  ]
} as const;

export const FEATURES = {
  "$comment": "Feature pillars per docs/AGENTS.md. The frontend uses these to generate nav + landing tiles; the backend uses them in audit-event types.",
  "features": [
    {
      "key": "region_atlas",
      "name": "Region Atlas",
      "summary": "Versioned region profiles with semantic-aware diff.",
      "icon": "globe",
      "route": "/regions"
    },
    {
      "key": "jjscan",
      "name": "JJSCAN+",
      "summary": "JCL static analysis with reason-tagged dispositions.",
      "icon": "scan",
      "route": "/jjscan"
    },
    {
      "key": "abend",
      "name": "ABEND Archaeologist",
      "summary": "SYSLOG + source triangulation with confidence tiers.",
      "icon": "bug",
      "route": "/abend"
    },
    {
      "key": "confidence_score",
      "name": "Confidence Score",
      "summary": "0\u2013100 readiness gauge composed across the other three.",
      "icon": "gauge",
      "route": "/confidence"
    },
    {
      "key": "review_queue",
      "name": "Review Queue",
      "summary": "Real-time team approval with mobile fallback.",
      "icon": "inbox",
      "route": "/review"
    }
  ]
} as const;

export const SEVERITIES = {
  "$comment": "Severity levels for findings. Order matters \u2014 sorted descending by impact.",
  "severities": [
    {
      "key": "critical",
      "label": "Critical",
      "default_deduction": 25
    },
    {
      "key": "high",
      "label": "High",
      "default_deduction": 10
    },
    {
      "key": "medium",
      "label": "Medium",
      "default_deduction": 5
    },
    {
      "key": "low",
      "label": "Low",
      "default_deduction": 2
    },
    {
      "key": "info",
      "label": "Info",
      "default_deduction": 0
    }
  ]
} as const;

export const STATUSES = {
  "$comment": "Status values used in jobs, queue, and finding dispositions.",
  "job_states": [
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled"
  ],
  "queue_states": [
    "pending_review",
    "approved",
    "rejected",
    "auto_approved",
    "expired"
  ],
  "finding_decisions": [
    "pending",
    "accept",
    "dismiss",
    "auto_fixed"
  ],
  "abend_tiers": [
    "confirmed",
    "probable",
    "unfamiliar",
    "unknown"
  ],
  "region_tiers": [
    "sandbox",
    "development",
    "integration",
    "production"
  ]
} as const;
