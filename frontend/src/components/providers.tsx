"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { rehydrateAuthFromStorage } from "@/lib/api/auth";
import { env } from "@/lib/env";
import { ToastProvider } from "@/components/ui/toast";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: (failureCount, err) => {
              const status = (err as { status?: number })?.status;
              if (status && status >= 400 && status < 500) return false;
              return failureCount < 2;
            },
          },
        },
      }),
  );

  const [mswReady, setMswReady] = useState(!env.useMsw);

  useEffect(() => {
    rehydrateAuthFromStorage();
    if (env.useMsw) {
      void import("@/mocks/browser").then((m) => m.startMockWorker().then(() => setMswReady(true)));
    }
  }, []);

  if (!mswReady) {
    return (
      <div className="flex min-h-screen items-center justify-center text-fg-muted">
        Booting mock backend…
      </div>
    );
  }

  return (
    <QueryClientProvider client={client}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
