"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/ui/page-header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import { FindingsList } from "@/features/jjscan/findings-list";
import { autoFixFinding, decideFinding, getScanJob } from "@/lib/api/jjscan";
import { queryKeys } from "@/lib/api/keys";

const REASON_LABELS: Record<string, string> = {
  false_positive: "false positive",
  shop_policy: "shop policy",
  intentional_override: "intentional override",
  resolved_offline: "resolved offline",
  custom: "custom note",
};

export default function ScanJobClient({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const toast = useToast();

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
    onSuccess: (_data, vars) => {
      const verb = vars.decision === "accept" ? "Accepted" : "Dismissed";
      toast.success(verb, `Reason: ${REASON_LABELS[vars.tag] ?? vars.tag}`);
      queryClient.invalidateQueries({ queryKey: queryKeys.jjscan.job(id) });
    },
    onError: (err: Error) => toast.error("Decision failed", err.message ?? "Unknown error"),
  });

  const autoFix = useMutation({
    mutationFn: (findingId: string) => autoFixFinding(findingId),
    onSuccess: () => {
      toast.success("Auto-fix applied", "Audit event written");
      queryClient.invalidateQueries({ queryKey: queryKeys.jjscan.job(id) });
    },
    onError: (err: Error) => toast.error("Auto-fix failed", err.message ?? "Unknown error"),
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
          dissent={{
            "JJ-COPYBOOK-DRIFT-001": {
              dismissedCount: 7,
              totalCount: 9,
              topReason: "Pinned by shop policy at the SYSLIB-chain level",
            },
          }}
          onDecide={(findingId, decision, tag) => decide.mutate({ findingId, decision, tag })}
          onAutoFix={(findingId) => autoFix.mutate(findingId)}
        />
      )}
    </>
  );
}
