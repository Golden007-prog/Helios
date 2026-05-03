// Query key factories — every key starts with the feature segment so a
// targeted invalidation can wipe one feature's cache without touching
// the rest.

export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  regions: {
    all: () => ["regions"] as const,
    list: (tier?: string) => ["regions", "list", tier ?? "all"] as const,
    detail: (name: string) => ["regions", "detail", name] as const,
    diff: (a: string, b: string) => ["regions", "diff", a, b] as const,
  },
  jjscan: {
    all: () => ["jjscan"] as const,
    job: (id: string) => ["jjscan", "job", id] as const,
    findings: (jobId: string) => ["jjscan", "findings", jobId] as const,
  },
  abend: {
    all: () => ["abend"] as const,
    detail: (id: string) => ["abend", "detail", id] as const,
    history: () => ["abend", "history"] as const,
  },
  score: {
    weights: (region: string) => ["score", "weights", region] as const,
    compute: (jclName: string, region: string) =>
      ["score", "compute", jclName, region] as const,
  },
  queue: {
    all: () => ["queue"] as const,
    list: () => ["queue", "list"] as const,
  },
  audit: {
    list: (filters?: Record<string, string>) =>
      ["audit", "list", filters ?? null] as const,
  },
  runbooks: {
    list: (filters?: Record<string, string>) =>
      ["runbooks", "list", filters ?? null] as const,
  },
} as const;
