"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { RegionTierBadge } from "@/features/regions/region-tier-badge";
import { getRegion } from "@/lib/api/regions";
import { queryKeys } from "@/lib/api/keys";

export default function RegionDetailPage() {
  const params = useParams<{ id: string }>();
  const name = params.id;

  const region = useQuery({
    queryKey: queryKeys.regions.detail(name),
    queryFn: () => getRegion(name),
  });

  if (region.isLoading) return <Skeleton className="h-64" />;
  if (region.isError)
    return (
      <p className="text-danger">Couldn&apos;t load region: {(region.error as Error).message}</p>
    );
  if (!region.data) return null;

  const r = region.data;
  return (
    <>
      <Breadcrumbs items={[{ label: "Region Atlas", href: "/regions" }, { label: r.name }]} />
      <PageHeader
        title={r.name}
        description="Versioned profile. Diff against any other region for promote-readiness."
        action={
          <Button asChild variant="secondary">
            <Link href={`/regions/${r.name}/diff`}>Diff…</Link>
          </Button>
        }
      />
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <CardTitle>Profile</CardTitle>
            <RegionTierBadge tier={r.tier} />
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
            <Row label="HLQ" value={<span className="font-mono">{r.hlq}</span>} />
            <Row label="DB2 subsystem" value={r.db2?.subsystem_id ?? "—"} />
            <Row label="DB2 plan collection" value={r.db2?.plan_collection ?? "—"} />
            <Row label="RACF group" value={r.racf_group ?? "—"} />
            <Row label="Scheduler queue" value={r.scheduler_queue ?? "—"} />
            <Row label="Volser pattern" value={r.volser_pattern ?? "—"} />
          </dl>
          {r.protected_resources && r.protected_resources.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-1 text-sm font-medium">Protected resources</h4>
              <ul className="list-disc pl-5 text-sm font-mono">
                {r.protected_resources.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-2 last:border-b-0">
      <dt className="text-fg-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
