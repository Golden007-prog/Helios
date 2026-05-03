import { apiRequest } from "./client";
import type { Finding, ScoreBreakdown } from "./types";

export interface ScoreRequest {
  jcl_source: string;
  target_region: string;
  findings: Finding[];
}

export async function computeScore(req: ScoreRequest): Promise<ScoreBreakdown> {
  return apiRequest<ScoreBreakdown>("/api/score", { method: "POST", json: req });
}

export async function getRegionWeights(region: string): Promise<Record<string, number>> {
  return apiRequest<Record<string, number>>(
    `/api/score/weights/${encodeURIComponent(region)}`,
  );
}
