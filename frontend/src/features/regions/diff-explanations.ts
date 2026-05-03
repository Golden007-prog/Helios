/**
 * Tooltip text mapping diff paths to plain-English "why this matters"
 * for the region diff viewer. Maps both exact paths and prefixes; longer
 * prefixes win.
 */
const EXPLANATIONS: Record<string, string> = {
  hlq: "Top-level dataset prefix. Mismatched HLQ means substitution rewrites every DSN reference in the JCL.",
  "db2.subsystem_id":
    "DB2 subsystem the job binds against. Wrong subsystem = SQLCODE -805 within seconds of program start.",
  "db2.plan_collection":
    "DB2 plan / collection the program package binds into. Missing plan in target = job won't run.",
  racf_group:
    "RACF group used as default authorization. Mismatch can cause SQLCODE -922 or open failures.",
  "jes.class_":
    "JES execution class. Drives priority + initiator selection; production typically uses a dedicated class.",
  "jes.sysout_class": "JES sysout class. Wrong class can route prints to the wrong destination.",
  scheduler_queue:
    "Scheduler queue the job is submitted into. Mismatch = job lands on the wrong tier's batch window.",
  volser_pattern:
    "Volume serial pattern for new dataset allocations. Mismatch can cause D37 out-of-space if volsers are sized differently.",
  protected_resources:
    "Resources requiring a paired backup before destructive ops. Drives the backup_gap penalty in Confidence Score.",
  gdg_retention:
    "GDG generation retention count. Different retention = downstream jobs may read the wrong generation.",
  confidence_weight_overrides:
    "Per-region overrides for the Confidence Score formula. Stricter weights = lower scores at the same finding count.",
  tier: "Region tier (development / integration / production). Drives review-required defaults and gating thresholds.",
};

export function explainPath(path: string): string | null {
  if (path in EXPLANATIONS) {
    return EXPLANATIONS[path] ?? null;
  }
  // Prefix match for nested paths — protected_resources[0] -> protected_resources.
  const prefix = path.split(/[.[]/, 1)[0];
  if (!prefix) return null;
  return EXPLANATIONS[prefix] ?? null;
}
