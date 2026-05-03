import ScanJobClient from "./client";

// Static-export needs every dynamic param pre-listed. We pre-render a
// "placeholder" + a couple of safe demo IDs (no colons — Windows static
// export can't write those filenames). Runtime IDs that aren't in the
// list (e.g. ``job:mock`` from MSW) are served via the public/404.html
// SPA fallback, which restores the original path on the client side.
const SCAN_JOB_IDS = ["placeholder", "job-mock", "CUST_DELETE_INACTIVE", "ZBNKDEL"] as const;

// dynamicParams=true means Next will attempt runtime lookup for any param
// not in this list. Combined with the SPA fallback in public/404.html, an
// arbitrary runtime ID still works: 404.html bounces to /Helios/jjscan/[id]/
// which is pre-rendered and the client component reads the actual id from
// useParams() once hydrated.
export const dynamicParams = true;

export function generateStaticParams() {
  return SCAN_JOB_IDS.map((id) => ({ id }));
}

export default function ScanJobPage({ params }: { params: { id: string } }) {
  return <ScanJobClient id={params.id} />;
}
