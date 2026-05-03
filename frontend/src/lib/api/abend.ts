import { apiRequest } from "./client";
import type { AbendEvent } from "./types";

export async function analyzeAbend(payload: {
  syslog: string;
  program?: string;
  source?: string;
}): Promise<AbendEvent> {
  return apiRequest<AbendEvent>("/api/abend", { method: "POST", json: payload });
}

export async function listAbendHistory(): Promise<{ events: AbendEvent[] }> {
  return apiRequest<{ events: AbendEvent[] }>("/api/abend/history");
}

export async function resolveAbend(
  eventId: string,
  resolution: { fix: string; runbook?: string },
): Promise<void> {
  await apiRequest<void>(`/api/abend/${encodeURIComponent(eventId)}/resolve`, {
    method: "POST",
    json: resolution,
  });
}
