import ScanJobClient from "./client";

// Static-export needs ``generateStaticParams`` for every dynamic segment.
// Job IDs are runtime-generated, so we pre-render a placeholder shell and
// allow runtime paths via ``dynamicParams = true``. This page is a server
// component so it can export the param list; the interactive client logic
// lives in ``./client.tsx``.
export const dynamicParams = true;

export function generateStaticParams() {
  return [{ id: "placeholder" }];
}

export default function ScanJobPage({ params }: { params: { id: string } }) {
  return <ScanJobClient id={params.id} />;
}
