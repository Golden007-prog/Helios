import { apiRequest } from "./client";
import type { RegionDiffResponse, RegionListItem, RegionProfile } from "./types";

export interface RegionListResponse {
  regions: RegionListItem[];
  total: number;
}

export interface RegionUpsertResponse {
  name: string;
  audit_event_id: string;
  review_required: boolean;
}

export async function listRegions(tier?: string): Promise<RegionListResponse> {
  return apiRequest<RegionListResponse>("/api/regions", { query: { tier } });
}

export async function getRegion(name: string): Promise<RegionProfile> {
  return apiRequest<RegionProfile>(`/api/regions/${encodeURIComponent(name)}`);
}

export async function upsertRegion(
  name: string,
  profile: RegionProfile,
  reason: string,
): Promise<RegionUpsertResponse> {
  return apiRequest<RegionUpsertResponse>(`/api/regions/${encodeURIComponent(name)}`, {
    method: "POST",
    json: { profile, reason },
  });
}

export async function diffRegions(a: string, b: string): Promise<RegionDiffResponse> {
  return apiRequest<RegionDiffResponse>(
    `/api/regions/${encodeURIComponent(a)}/diff/${encodeURIComponent(b)}`,
  );
}
