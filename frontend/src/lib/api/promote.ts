import { apiRequest } from "./client";

export interface PromoteRequest {
  jcl_source?: string;
  jcl_name?: string;
  source_region: string;
  target_region: string;
  apply_auto_fixes?: boolean;
  reason?: string;
}

export interface PromoteResponse {
  promote_id: string;
  rewritten_jcl: string;
  score: number;
  findings_count: number;
  review_required: boolean;
  audit_event_id: string;
}

export async function promote(req: PromoteRequest): Promise<PromoteResponse> {
  return apiRequest<PromoteResponse>("/api/promote", { method: "POST", json: req });
}
