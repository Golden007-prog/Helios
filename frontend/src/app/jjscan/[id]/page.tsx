"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/ui/page-header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { BobStub } from "@/components/ui/bob-stub";
import { Badge } from "@/components/ui/badge";
import { getScanJob } from "@/lib/api/jjscan";
import { queryKeys } from "@/lib/api/keys";

export default function ScanJobPage() {
  const { id } = useParams<{ id: string }>();
  const job = useQuery({
    queryKey: queryKeys.jjscan.job(id),
    queryFn: () => getScanJob(id),
    refetchInterval: (q) => {
      const state = q.state.data?.state;
      return state === "pending" || state === "running" ? 1500 : false;
    },
  });

  return (
    <>
      <Breadcrumbs items={[{ label: "JJSCAN+", href: "/jjscan" }, { label: id }]} />
      <PageHeader
        title="Scan results"
        action={
          job.data && (
            <Badge
              variant={
                job.data.state === "succeeded"
                  ? "low"
                  : job.data.state === "failed"
                    ? "critical"
                    : "neutral"
              }
            >
              {job.data.state}
            </Badge>
          )
        }
      />
      {job.isLoading && <Skeleton className="h-64" />}
      {/* BOB: result-rendering component is reserved for Bob (docs/PHASE_PLAN.md §1.3).
          Page shell + status polling + breadcrumbs + Maya-friendly copy is here.
          Bob renders the findings list with auto-fix CTAs, dissent banners,
          reason-tag pickers per docs/JJSCAN_PLUS_RULES.md and docs/LEARNING_LOOP.md. */}
      <BobStub
        feature="JJSCAN+ result viewer"
        spec="Render findings grouped by severity with auto-fix CTAs, dissent banner inline (per docs/LEARNING_LOOP.md), and reason-tag picker on accept/dismiss. Fed by GET /api/scan/{id}.findings."
      />
    </>
  );
}
