// Read public env vars in one place so misuses are obvious in PR review.

export const env = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080",
  useMsw: process.env.NEXT_PUBLIC_USE_MSW === "true",
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? "",
} as const;
