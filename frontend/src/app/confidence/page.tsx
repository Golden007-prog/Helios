"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfidenceGauge } from "@/features/score/confidence-gauge";
import { toGaugeBreakdown } from "@/features/score/score-breakdown";
import { computeScore } from "@/lib/api/score";
import { queryKeys } from "@/lib/api/keys";

const HERO_JCL = "CUST_DELETE_INACTIVE";
const HERO_REGION = "int3";

export default function ConfidencePage() {
  const queryClient = useQueryClient();
  const [appliedFixes, setAppliedFixes] = useState<Set<string>>(new Set());

  const score = useQuery({
    queryKey: queryKeys.score.compute(HERO_JCL, HERO_REGION),
    queryFn: () => computeScore({ jcl_name: HERO_JCL, region: HERO_REGION }),
  });

  const applyFix = useMutation({
    mutationFn: async (key: string) => {
      // The auto-fix application API isn't wired yet; this mutates the
      // local "applied" set so the demo can simulate the score-recompute
      // flow. When the backend lands the auto-fix endpoint, swap this for
      // a real POST.
      setAppliedFixes((prev) => new Set([...prev, key]));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.score.compute(HERO_JCL, HERO_REGION),
      });
    },
  });

  // Filter the deductions client-side based on which fixes the user
  // has already applied — keeps the gauge honest about what's left.
  const breakdown = score.data?.breakdown ? toGaugeBreakdown(score.data.breakdown) : null;
  const remainingDeductions = breakdown?.deductions.filter((d) => !appliedFixes.has(d.key)) ?? [];
  const remainingPenalty = remainingDeductions.reduce((sum, d) => sum + d.amount, 0);
  const totalBoost = breakdown?.boosts.reduce((sum, b) => sum + b.amount, 0) ?? 0;
  const liveScore = score.data
    ? Math.max(0, Math.min(100, (score.data.breakdown.base ?? 100) - remainingPenalty + totalBoost))
    : 0;

  return (
    <>
      <PageHeader
        title="Confidence Score"
        description="0–100 readiness wrapper composed from JJSCAN+ findings, region mismatch, backup-gap, and historical ABEND priors."
      />
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>How it composes</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            <li>Severity-weighted JJSCAN+ deductions (per-region overridable).</li>
            <li>Region mismatch count (HLQ, DB2, RACF, JES, scheduler, volser, GDG retention).</li>
            <li>
              Backup-gap signal: protected resources without a paired UNLOAD/IMAGE COPY/REPRO.
            </li>
            <li>Historical ABEND priors for the program in the target region.</li>
          </ul>
        </CardContent>
      </Card>

      {score.isLoading && <Skeleton className="h-72" />}
      {score.isError && (
        <Card>
          <CardContent className="py-6 text-sm text-danger">
            Failed to load score: {(score.error as Error).message}
          </CardContent>
        </Card>
      )}
      {score.data && breakdown && (
        <ConfidenceGauge
          score={liveScore}
          base={score.data.breakdown.base ?? 100}
          deductions={remainingDeductions}
          boosts={breakdown.boosts}
          subjectName={HERO_JCL}
          onApplyAutoFix={(key) => applyFix.mutate(key)}
          onOverride={() => {
            // Override modal is out of scope for this turn; emit a
            // console event so reviewers can spot the click during demo.
            // eslint-disable-next-line no-console
            console.info("[helios] override-score clicked for", HERO_JCL);
          }}
        />
      )}
    </>
  );
}
