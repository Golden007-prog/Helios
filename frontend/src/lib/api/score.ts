import { apiRequest } from "./client";

/** Backend ``/api/score`` request body. Either ``jcl_source`` or
 * ``jcl_name`` is provided. */
export interface ScoreRequest {
  jcl_source?: string;
  jcl_name?: string;
  region: string;
}

/** Rich breakdown returned by ``app.services.score.compute`` — flat
 * ``{deductions, boosts}`` dicts keyed by component name. */
export interface ServerScoreBreakdown {
  base: number;
  deductions: Record<string, number>;
  boosts: Record<string, number>;
}

export interface ScoreResponse {
  score: number;
  breakdown: ServerScoreBreakdown;
}

export async function computeScore(req: ScoreRequest): Promise<ScoreResponse> {
  return apiRequest<ScoreResponse>("/api/score", { method: "POST", json: req });
}

export async function getRegionWeights(region: string): Promise<Record<string, number>> {
  return apiRequest<Record<string, number>>(`/api/score/weights/${encodeURIComponent(region)}`);
}
