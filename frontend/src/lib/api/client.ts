import { env } from "@/lib/env";

export type Envelope<T> = { ok: true; data: T; request_id: string };
export type ErrorEnvelope = {
  ok: false;
  error: { code: string; message: string; details?: Record<string, unknown> };
  request_id: string;
};

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public requestId: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
  }
}

let authToken: string | null = null;
export function setAuthToken(token: string | null) {
  authToken = token;
}
export function getAuthToken(): string | null {
  return authToken;
}

type Method = "GET" | "POST" | "PUT" | "DELETE";

interface RequestOptions {
  method?: Method;
  json?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", json, query, signal } = options;

  const url = new URL(path, env.apiBaseUrl || window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  if (json !== undefined) headers["Content-Type"] = "application/json";
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: json !== undefined ? JSON.stringify(json) : undefined,
    signal,
    credentials: "include",
  });

  const requestId = res.headers.get("X-Request-ID") ?? "req:unknown";

  if (res.status === 204) {
    // typed as T by caller
    return undefined as unknown as T;
  }

  let body: unknown;
  try {
    body = await res.json();
  } catch {
    throw new ApiError("INVALID_RESPONSE", res.statusText, res.status, requestId);
  }

  if (!res.ok || (body as ErrorEnvelope).ok === false) {
    const err = (body as ErrorEnvelope).error;
    throw new ApiError(
      err?.code ?? "UNKNOWN",
      err?.message ?? res.statusText,
      res.status,
      requestId,
      err?.details,
    );
  }

  return (body as Envelope<T>).data;
}
