import { apiRequest, setAuthToken } from "./client";
import type { User } from "./types";

interface LoginResponse {
  token: string;
  expires_at: string;
  user: User;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    json: { email, password },
  });
  setAuthToken(data.token);
  if (typeof window !== "undefined") {
    window.localStorage.setItem("helios_token", data.token);
  }
  return data;
}

export async function logout(): Promise<void> {
  try {
    await apiRequest<void>("/auth/logout", { method: "POST" });
  } finally {
    setAuthToken(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("helios_token");
    }
  }
}

export async function fetchMe(): Promise<{ user: User }> {
  return apiRequest<{ user: User }>("/auth/me");
}

export function rehydrateAuthFromStorage(): string | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem("helios_token");
  if (token) setAuthToken(token);
  return token;
}
