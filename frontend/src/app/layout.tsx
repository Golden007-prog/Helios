import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AppShell } from "@/components/layout/app-shell";

export const metadata: Metadata = {
  title: "Helios — AI control plane for z/OS modernization",
  description:
    "Helios turns tribal knowledge about regions, dependencies, and ABENDs into versioned, queryable, learnable artifacts.",
};

// SPA fallback restorer (paired with public/404.html). When 404.html
// redirects an unknown deep-link to the root with ?p=/path&q=query, this
// snippet rewrites the browser URL via history.replaceState before the
// client router boots, so Next picks up the right route.
const SPA_FALLBACK_SNIPPET = `
(function(l){
  if (l.search[1] === 'p') {
    var decoded = l.search.slice(1).split('&').map(function(s){return s.replace(/~and~/g,'&');}),
        path = '',
        query = '';
    decoded.forEach(function(p){
      if (p.indexOf('p=') === 0) path = p.slice(2);
      else if (p.indexOf('q=') === 0) query = '?' + p.slice(2);
    });
    if (path) {
      window.history.replaceState(null, null, l.pathname.replace(/\\/$/, '') + path + query + l.hash);
    }
  }
})(window.location);
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <Script
          id="spa-fallback-restore"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: SPA_FALLBACK_SNIPPET }}
        />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
