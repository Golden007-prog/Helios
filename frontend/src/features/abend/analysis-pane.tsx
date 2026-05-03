"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { AbendAnalysisResponse } from "./types";

export interface AnalysisPaneProps {
  abend: AbendAnalysisResponse;
  /** Called when "Apply quarantine SQL" is clicked. Only enabled in the
   * confirmed tier with quarantine SQL present. */
  onApplyQuarantine?: (sql: string) => void;
  /** Called when the resolution form is submitted. */
  onSubmitResolution?: (text: string) => void;
  /** Called when the user clicks "Submit pattern to learning loop". */
  onSubmitPattern?: () => void;
}

const TIER_VARIANT: Record<
  AbendAnalysisResponse["identified_abend"]["tier"],
  "low" | "medium" | "critical" | "info"
> = {
  confirmed: "low",
  probable: "medium",
  unfamiliar: "critical",
  unknown: "info",
};

const TIER_LABEL: Record<AbendAnalysisResponse["identified_abend"]["tier"], string> = {
  confirmed: "Confirmed",
  probable: "Probable",
  unfamiliar: "Unfamiliar — submit a pattern",
  unknown: "Unknown",
};

export function AnalysisPane({
  abend,
  onApplyQuarantine,
  onSubmitResolution,
  onSubmitPattern,
}: AnalysisPaneProps) {
  const [resolutionText, setResolutionText] = useState("");
  const tier = abend.identified_abend.tier;
  const isUnfamiliar = tier === "unfamiliar";

  const canQuarantine = tier === "confirmed" && Boolean(abend.quarantine_sql);

  return (
    <div className="flex h-full flex-col gap-3" data-testid="analysis-pane">
      <header>
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">
            Identified ABEND: <span className="font-mono">{abend.identified_abend.code}</span>
          </h2>
          <Badge variant={TIER_VARIANT[tier]} data-testid={`tier-${tier}`}>
            {TIER_LABEL[tier]}
          </Badge>
        </div>
        <p className="mt-1 text-xs text-fg-muted">
          Confidence: {Math.round(abend.identified_abend.confidence * 100)}%
        </p>
      </header>

      {isUnfamiliar && (
        <div
          className="rounded-md border border-danger/40 bg-danger/5 p-3 text-xs"
          data-testid="unfamiliar-banner"
        >
          <strong className="font-semibold">Hasn't seen this before.</strong> The pattern library
          couldn't classify this dump. Submit it to the learning loop so future runs can match it.
          {onSubmitPattern && (
            <Button size="sm" className="mt-2 block" onClick={onSubmitPattern}>
              Submit pattern
            </Button>
          )}
        </div>
      )}

      {abend.business_rule_explanation && (
        <Card>
          <CardContent className="py-3 text-sm">{abend.business_rule_explanation}</CardContent>
        </Card>
      )}

      {abend.ranked_root_causes.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-fg-muted">
            Ranked root causes
          </h3>
          <ol className="space-y-1">
            {abend.ranked_root_causes.map((c, i) => (
              <li
                key={i}
                className="flex items-start justify-between gap-3 rounded-md border border-border bg-bg-elev px-3 py-2 text-sm"
                data-testid={`cause-${i}`}
              >
                <div>
                  <div>{c.cause}</div>
                  <div className="text-xs text-fg-muted">
                    {c.prior_count} prior incidents · similarity {Math.round(c.confidence * 100)}%
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {abend.matching_runbooks.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-fg-muted">
            Matching runbooks
          </h3>
          <ul className="space-y-1">
            {abend.matching_runbooks.map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between rounded-md border border-border bg-bg-elev px-3 py-2 text-sm"
              >
                <div>
                  <div>{r.title}</div>
                  <div className="text-xs text-fg-muted">used {r.success_count}× successfully</div>
                </div>
                <a
                  href={`/runbooks/${encodeURIComponent(r.id)}`}
                  className="text-xs text-accent hover:underline"
                >
                  Open
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <Button
        size="sm"
        disabled={!canQuarantine}
        onClick={() => canQuarantine && onApplyQuarantine?.(abend.quarantine_sql ?? "")}
        className={cn(!canQuarantine && "opacity-60")}
        data-testid="apply-quarantine"
      >
        Apply quarantine SQL
      </Button>

      <section className="mt-auto">
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-fg-muted">
          Submit resolution
        </h3>
        <Textarea
          rows={3}
          placeholder="Describe what you did to resolve this…"
          value={resolutionText}
          onChange={(e) => setResolutionText(e.target.value)}
          data-testid="resolution-text"
        />
        <div className="mt-2 flex justify-end">
          <Button
            size="sm"
            disabled={resolutionText.trim().length === 0}
            onClick={() => {
              onSubmitResolution?.(resolutionText.trim());
              setResolutionText("");
            }}
            data-testid="submit-resolution"
          >
            Submit
          </Button>
        </div>
      </section>
    </div>
  );
}
