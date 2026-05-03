"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/ui/page-header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Badge } from "@/components/ui/badge";
import { FindingsList } from "@/features/jjscan/findings-list";
import { autoFixFinding, decideFinding, getScanJob } from "@/lib/api/jjscan";
import { queryKeys } from "@/lib/api/keys";

export default function ScanJobClient({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const job = useQuery({
    queryKey: queryKeys.jjscan.job(id),
    queryFn: () => getScanJob(id),
    refetchInterval: (q) => {
      const state = q.state.data?.state;
      return state === "pending" || state === "running" ? 1500 : false;
    },
  });

  const decide = useMutation({
    mutationFn: ({
      findingId,
      decision,
      tag,
    }: {
      findingId: string;
      decision: "accept" | "dismiss";
      tag: string;
    }) => decideFinding(findingId, decision, [tag]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jjscan.job(id) });
    },
  });

  const autoFix = useMutation({
    mutationFn: (findingId: string) => autoFixFinding(findingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jjscan.job(id) });
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
      {job.data && (
        <FindingsList
          findings={job.data.findings}
          onDecide={(findingId, decision, tag) =>
            decide.mutate({ findingId, decision, tag })
          }
          onAutoFix={(findingId) => autoFix.mutate(findingId)}
        />
      )}
    </>
  );
}
