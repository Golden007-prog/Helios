"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listQueue } from "@/lib/api/queue";
import { queryKeys } from "@/lib/api/keys";
import { env } from "@/lib/env";

export type ConnectionState = "live" | "connecting" | "polling" | "offline";

interface UseReviewQueueOptions {
  pollIntervalMs?: number;
  /** Called whenever a NEW pending event is observed (event_id was not in
   * the previous snapshot). Used by the page to fire toast notifications. */
  onNewPending?: (eventId: string) => void;
}

/**
 * Subscribe to the review queue.
 *
 * Strategy:
 * - Always run a polling ``useQuery`` with a generous interval (default
 *   5s). This is the always-on fallback the spec calls for and ensures
 *   the UI is never empty when the WebSocket can't connect.
 * - Additionally try to open a ``/api/ws/queue`` WebSocket. On every
 *   message we invalidate the polling query so the UI updates within
 *   the round-trip rather than waiting for the next poll tick.
 * - WebSocket reconnects with exponential backoff (1s, 2s, 4s, capped
 *   at 30s) up to ~10 attempts before falling permanently to polling.
 */
export function useReviewQueue(opts: UseReviewQueueOptions = {}) {
  const { pollIntervalMs = 5000, onNewPending } = opts;
  const queryClient = useQueryClient();
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const previousIds = useRef<Set<string>>(new Set());

  const query = useQuery({
    queryKey: queryKeys.queue.list(),
    queryFn: () => listQueue(),
    refetchInterval: pollIntervalMs,
  });

  // Track new pending events on every successful poll / refetch.
  useEffect(() => {
    if (!query.data) return;
    const ids = new Set(query.data.items.map((i) => i.event_id));
    for (const id of ids) {
      if (!previousIds.current.has(id)) {
        // Skip the first snapshot — every event is "new" relative to ∅.
        if (previousIds.current.size > 0) {
          onNewPending?.(id);
        }
      }
    }
    previousIds.current = ids;
  }, [query.data, onNewPending]);

  // WebSocket subscription with backoff. Skipped server-side and when MSW
  // is on (mock backend has no WS endpoint).
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (env.useMsw) {
      setConnection("polling");
      return;
    }
    let attempt = 0;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const open = () => {
      const wsUrl = env.apiBaseUrl.replace(/^http/, "ws") + "/api/ws/queue";
      try {
        socket = new WebSocket(wsUrl);
      } catch {
        scheduleReconnect();
        return;
      }
      setConnection("connecting");
      socket.onopen = () => {
        attempt = 0;
        setConnection("live");
      };
      socket.onmessage = () => {
        // The server publishes lightweight notifications — no payload
        // parsing needed here, just refresh the polling source of truth.
        queryClient.invalidateQueries({
          queryKey: queryKeys.queue.list(),
        });
      };
      socket.onerror = () => {
        // ``onclose`` is also fired; let it handle the schedule.
      };
      socket.onclose = () => {
        scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      if (attempt >= 10) {
        setConnection("polling");
        return;
      }
      const delay = Math.min(30000, 1000 * 2 ** attempt);
      attempt += 1;
      setConnection("polling");
      reconnectTimer = setTimeout(open, delay);
    };

    open();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket && socket.readyState !== WebSocket.CLOSED) {
        socket.close();
      }
    };
  }, [queryClient]);

  return {
    items: query.data?.items ?? [],
    isLoading: query.isLoading,
    error: query.error as Error | null,
    connection,
  };
}
