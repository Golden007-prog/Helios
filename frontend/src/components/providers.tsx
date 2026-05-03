"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { rehydrateAuthFromStorage } from "@/lib/api/auth";
import { setAuthToken } from "@/lib/api/client";
import { env } from "@/lib/env";
import { ToastProvider } from "@/components/ui/toast";

// Pages that don't require an authenticated session.
const PUBLIC_PATHS = new Set(["/login"]);

function isPublicPath(pathname: string): boolean {
  // Strip trailing slash and the static-export basePath so '/Helios/login/'
  // and '/login' both resolve to the same logical key.
  const stripped = pathname.replace(/\/+$/, "");
  if (PUBLIC_PATHS.has(stripped)) return true;
  for (const p of PUBLIC_PATHS) {
    if (stripped.endsWith(p)) return true;
  }
  return false;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: (failureCount, err) => {
              const status = (err as { status?: number })?.status;
              // 401 = re-auth, 403 = forbidden (different fix), 404 = stable
              if (status === 401) {
                setAuthToken(null);
                if (typeof window !== "undefined") {
                  window.localStorage.removeItem("helios_token");
                  if (!isPublicPath(window.location.pathname)) {
                    window.location.href = "/login";
                  }
                }
                return false;
              }
              if (status && status >= 400 && status < 500) return false;
              return failureCount < 2;
            },
          },
        },
      }),
  );

  const [mswReady, setMswReady] = useState(!env.useMsw);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const token = rehydrateAuthFromStorage();
    setAuthChecked(true);
    if (!token && pathname && !isPublicPath(pathname)) {
      router.replace("/login");
    }
    if (env.useMsw) {
      void import("@/mocks/browser").then((m) =>
        m.startMockWorker().then(() => setMswReady(true)),
      );
    }
    // pathname intentionally omitted — we only check on initial mount;
    // re-auth on route change is handled by the 401 retry above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!mswReady || !authChecked) {
    return (
      <div className="flex min-h-screen items-center justify-center text-fg-muted">
        {!authChecked ? "Loading…" : "Booting mock backend…"}
      </div>
    );
  }

  return (
    <QueryClientProvider client={client}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
