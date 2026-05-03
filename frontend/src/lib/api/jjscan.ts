import { apiRequest } from "./client";
import type { ScanJob } from "./types";

export interface ScanRequest {
  jcl_source?: string;
  jcl_name?: string;
  target_region: string;
}

export async function submitScan(req: ScanRequest): Promise<{ job_id: string }> {
  return apiRequest<{ job_id: string }>("/api/scan", { method: "POST", json: req });
}

export async function getScanJob(id: string): Promise<ScanJob> {
  return apiRequest<ScanJob>(`/api/scan/${encodeURIComponent(id)}`);
}

export async function decideFinding(
  findingId: string,
  decision: "accept" | "dismiss",
  reasonTags: string[],
): Promise<void> {
  await apiRequest<void>(`/api/scan/findings/${encodeURIComponent(findingId)}/decide`, {
    method: "POST",
    json: { decision, reason_tags: reasonTags },
  });
}

export async function autoFixFinding(findingId: string): Promise<void> {
  await apiRequest<void>(`/api/scan/findings/${encodeURIComponent(findingId)}/auto-fix`, {
    method: "POST",
  });
}
