"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { BobStub } from "@/components/ui/bob-stub";
import { listRegions } from "@/lib/api/regions";
import { queryKeys } from "@/lib/api/keys";

export default function RegionDiffPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const a = params.id;
  const b = search.get("vs") ?? "";

  const all = useQuery({ queryKey: queryKeys.regions.list(), queryFn: () => listRegions() });

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

      {/* BOB: hero-shot diff view, see docs/AGENTS.md / docs/PHASE_PLAN.md §1.2.
          Layout is here (header + region picker + diff panel area). The actual
          field-by-field diff renderer is Bob's. The backend endpoint
          GET /api/regions/{a}/diff/{b} returns a 501 until Bob lands the
          algorithm. */}
      <BobStub
        feature="Region Atlas diff renderer"
        spec="Side-by-side or unified field-by-field renderer powered by GET /api/regions/{a}/diff/{b}. Hover-reasons, color-coded value_change/added/removed, monaco-quality typography. P95 < 250 ms render budget per docs/TESTING.md §5."
      />
    </>
  );
}
