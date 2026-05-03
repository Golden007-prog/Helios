import { apiRequest } from "./client";
import type { QueueItem } from "./types";

export async function listQueue(): Promise<{ items: QueueItem[] }> {
  return apiRequest<{ items: QueueItem[] }>("/api/queue");
}

export async function approveQueueItem(eventId: string, comment?: string): Promise<void> {
  await apiRequest<void>(`/api/queue/${encodeURIComponent(eventId)}/approve`, {
    method: "POST",
    json: { comment },
  });
}

export async function rejectQueueItem(eventId: string, reason: string): Promise<void> {
  await apiRequest<void>(`/api/queue/${encodeURIComponent(eventId)}/reject`, {
    method: "POST",
    json: { reason },
  });
}
