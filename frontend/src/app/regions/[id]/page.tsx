import RegionDetailClient from "./client";

// Static-export needs every dynamic param pre-listed. The set matches the
// MSW fixtures (frontend/src/mocks/fixtures.ts:REGIONS) so every region
// card in the list view has a live detail page on Pages.
const REGION_IDS = ["sandbox", "dev1", "dev2", "int2", "int3", "prod", "dr"] as const;

export const dynamicParams = false;

export function generateStaticParams() {
  return REGION_IDS.map((id) => ({ id }));
}

export default function RegionDetailPage({ params }: { params: { id: string } }) {
  return <RegionDetailClient id={params.id} />;
}
