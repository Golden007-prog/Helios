"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { RegionDiffViewer } from "@/features/regions/region-diff-viewer";
import { diffRegions, listRegions } from "@/lib/api/regions";
import { queryKeys } from "@/lib/api/keys";

export default function RegionDiffClient({ id }: { id: string }) {
  const search = useSearchParams();
  const router = useRouter();
  const a = id;
  const b = search.get("vs") ?? "";

  const all = useQuery({ queryKey: queryKeys.regions.list(), queryFn: () => listRegions() });
  const diff = useQuery({
    queryKey: queryKeys.regions.diff(a, b),
    queryFn: () => diffRegions(a, b),
    enabled: Boolean(b),
  });

  return (
    <>
      <Breadcrumbs
        items={[
          { label: "Region Atlas", href: "/regions" },
          { label: a, href: `/regions/${a}` },
          { label: "Diff" },
        ]}
      />
      <PageHeader title={`Diff: ${a} ↔ ${b || "(pick a region)"}`} />
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Choose a region to compare with</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {all.data?.regions
              .filter((r) => r.name !== a)
              .map((r) => (
                <a
                  key={r.name}
                  href={`?vs=${r.name}`}
                  className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-bg-subtle"
                >
                  {r.name}
                </a>
              ))}
          </div>
        </CardContent>
      </Card>

      {b && diff.isLoading && <Skeleton className="h-64" />}
      {b && diff.isError && (
        <Card>
          <CardContent className="py-6 text-sm text-danger">
            Failed to load diff: {(diff.error as Error).message}
          </CardContent>
        </Card>
      )}
      {b && diff.data && (
        <RegionDiffViewer
          regionA={diff.data.a}
          regionB={diff.data.b}
          fields={diff.data.fields}
          onSwap={() => router.replace(`/regions/${b}/diff?vs=${a}`)}
        />
      )}
    </>
  );
}
