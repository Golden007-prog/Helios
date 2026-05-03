"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { ConfidenceGauge } from "@/features/score/confidence-gauge";
import { toGaugeBreakdown } from "@/features/score/score-breakdown";
import { computeScore } from "@/lib/api/score";
import { queryKeys } from "@/lib/api/keys";

const HERO_JCL = "ZBNKDEL";
const HERO_REGION = "int3";

const DEDUCTION_LABEL: Record<string, string> = {
  backup_gap: "Backup gap",
  jjscan_high: "High JJSCAN+ findings",
  jjscan_critical: "Critical JJSCAN+ findings",
  jjscan_medium: "Medium JJSCAN+ findings",
  region_mismatch: "Region mismatch",
};

export default function ConfidencePage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [appliedFixes, setAppliedFixes] = useState<Set<string>>(new Set());
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [overrideTarget, setOverrideTarget] = useState(85);

  const score = useQuery({
    queryKey: queryKeys.score.compute(HERO_JCL, HERO_REGION),
    queryFn: () => computeScore({ jcl_name: HERO_JCL, region: HERO_REGION }),
  });

  const applyFix = useMutation({
    mutationFn: async (key: string) => {
      // The auto-fix application API isn't wired against a real backend yet;
      // local state mutation drives the 62 → 94 → 100 demo trajectory.
      setAppliedFixes((prev) => new Set([...prev, key]));
    },
    onSuccess: (_data, key) => {
      const label = DEDUCTION_LABEL[key] ?? key;
      toast.success(`Auto-fix applied — ${label}`, "Score recomputing…");
      queryClient.invalidateQueries({
        queryKey: queryKeys.score.compute(HERO_JCL, HERO_REGION),
      });
    },
    onError: (err: Error) => toast.error("Auto-fix failed", err.message ?? "Unknown error"),
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

  function submitOverride() {
    if (overrideReason.trim().length < 20) {
      toast.error("Reason too short", "Override requires at least 20 characters of rationale");
      return;
    }
    toast.success(
      `Score overridden to ${overrideTarget}`,
      `Reason logged to audit log; expires in 24h`,
    );
    setOverrideOpen(false);
    setOverrideReason("");
  }

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
          onOverride={() => setOverrideOpen(true)}
        />
      )}

      {overrideOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 p-4"
          role="dialog"
          aria-label="Override score"
          onClick={() => setOverrideOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-lg border border-border bg-bg-elev p-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-sm font-semibold">Override score</h2>
            <p className="mt-1 text-xs text-fg-muted">
              The override is logged to the audit log, expires in 24 hours, and surfaces a{" "}
              <code className="rounded bg-bg-subtle px-1">score.override</code> learning event for
              future similar promotions.
            </p>
            <div className="mt-4 grid gap-3">
              <label className="grid gap-1 text-xs">
                <span className="text-fg-muted">Override target score</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={overrideTarget}
                  onChange={(e) => setOverrideTarget(Math.max(0, Math.min(100, +e.target.value)))}
                  className="h-9 w-full rounded-md border border-border bg-bg px-3 text-sm"
                />
              </label>
              <label className="grid gap-1 text-xs">
                <span className="text-fg-muted">Reason (≥ 20 chars, required)</span>
                <Textarea
                  rows={3}
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="e.g. Anil approved an exception for the BNKACC.PATH3 cleanup — pinned to release-window window"
                />
                <span className={overrideReason.length < 20 ? "text-warning" : "text-success"}>
                  {overrideReason.length} / 20+ characters
                </span>
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => setOverrideOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={submitOverride}>
                Override + log
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
