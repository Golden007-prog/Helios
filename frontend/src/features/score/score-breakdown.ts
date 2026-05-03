import type { ScoreBreakdownLine } from "./confidence-gauge";

/**
 * Backend score response (rich shape from app.services.score.compute):
 *   { base: number, deductions: dict<str,int>, boosts: dict<str,int> }
 *
 * The gauge wants a flat list of {key, amount} rows. This module is the
 * adapter and the place to add per-key flags like ``autoFixable``.
 */
export interface ServerScoreBreakdown {
  base: number;
  deductions: Record<string, number>;
  boosts: Record<string, number>;
}

const AUTO_FIXABLE_KEYS = new Set([
  "backup_gap",
  "jjscan_high",
  "jjscan_critical",
  "jjscan_medium",
]);

export function toGaugeBreakdown(server: ServerScoreBreakdown): {
  deductions: ScoreBreakdownLine[];
  boosts: ScoreBreakdownLine[];
} {
  const deductions = Object.entries(server.deductions ?? {}).map<ScoreBreakdownLine>(
    ([key, amount]) => ({
      key,
      amount,
      autoFixable: AUTO_FIXABLE_KEYS.has(key),
    }),
  );
  const boosts = Object.entries(server.boosts ?? {}).map<ScoreBreakdownLine>(([key, amount]) => ({
    key,
    amount,
  }));
  return { deductions, boosts };
}
