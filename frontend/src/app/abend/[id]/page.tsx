import AbendDetailClient from "./client";

// No colons in IDs — Windows static export can't write filenames
// containing ``:``. Runtime colon-IDs from MSW (e.g. ``abend:demo:0001``)
// are served via the SPA fallback in public/404.html.
const ABEND_IDS = ["placeholder", "abend-demo-0001", "S0C7"] as const;

export const dynamicParams = true;

export function generateStaticParams() {
  return ABEND_IDS.map((id) => ({ id }));
}

export default function AbendDetailPage({ params }: { params: { id: string } }) {
  return <AbendDetailClient id={params.id} />;
}
