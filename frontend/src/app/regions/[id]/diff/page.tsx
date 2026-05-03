import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import RegionDiffClient from "./client";

const REGION_IDS = ["sandbox", "dev1", "dev2", "int2", "int3", "prod", "dr"] as const;

export const dynamicParams = false;

export function generateStaticParams() {
  return REGION_IDS.map((id) => ({ id }));
}

export default function RegionDiffPage({ params }: { params: { id: string } }) {
  // ``RegionDiffClient`` reads the ``vs`` query string via
  // ``useSearchParams``. When statically exported, Next 14 needs the
  // search-params reader to be inside a Suspense boundary so the static
  // shell can stream while the client picks up the URL.
  return (
    <Suspense fallback={<Skeleton className="h-64" />}>
      <RegionDiffClient id={params.id} />
    </Suspense>
  );
}
