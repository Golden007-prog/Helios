"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Finding, Severity } from "@/lib/api/types";

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

const SEVERITY_VARIANT: Record<Severity, "critical" | "high" | "medium" | "low" | "info"> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "info",
};

export type ReasonTag =
  | "false_positive"
  | "shop_policy"
  | "intentional_override"
  | "resolved_offline"
  | "custom";

export interface DissentInfo {
  /** Number of findings on similar jobs dismissed in the past. */
  dismissedCount: number;
  /** Total similar findings observed. */
  totalCount: number;
  /** Top reason teams gave when dismissing. */
  topReason?: string;
}

export interface FindingsListProps {
  findings: Finding[];
  /** Map of rule_id → dissent banner data. Drives the "7 of 9 teams
   * dismissed this" inline banner on matching findings. */
  dissent?: Record<string, DissentInfo>;
  onDecide?: (id: string, decision: "accept" | "dismiss", tag: ReasonTag) => void;
  onAutoFix?: (id: string) => void;
}

type DecidedState = "accepted" | "dismissed" | "auto-fixed";

/** Group findings by severity, in the canonical order. */
function groupBySeverity(findings: Finding[]): Record<Severity, Finding[]> {
  const out: Record<Severity, Finding[]> = {
    critical: [],
    high: [],
    medium: [],
    low: [],
    info: [],
  };
  for (const f of findings) out[f.severity]?.push(f);
  return out;
}

const REASON_TAGS: { value: ReasonTag; label: string }[] = [
  { value: "false_positive", label: "False positive" },
  { value: "shop_policy", label: "Shop policy" },
  { value: "intentional_override", label: "Intentional override" },
  { value: "resolved_offline", label: "Resolved offline" },
  { value: "custom", label: "Other (note in audit)" },
];

const DECIDED_LABEL: Record<DecidedState, string> = {
  accepted: "Accepted",
  dismissed: "Dismissed",
  "auto-fixed": "Auto-fixed",
};

const DECIDED_VARIANT: Record<DecidedState, "low" | "info" | "medium"> = {
  accepted: "low",
  dismissed: "info",
  "auto-fixed": "low",
};

export function FindingsList({ findings, dissent = {}, onDecide, onAutoFix }: FindingsListProps) {
  // Optimistic local state — track which findings the user has just
  // decided so the UI gives immediate visual feedback even when the
  // refetch returns the same list (mock backends do that).
  const [decided, setDecided] = useState<Record<string, DecidedState>>({});
  const [collapsed, setCollapsed] = useState<Set<Severity>>(new Set());
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
  const [reasonPicker, setReasonPicker] = useState<{
    findingId: string;
    decision: "accept" | "dismiss";
  } | null>(null);
  const [showResolved, setShowResolved] = useState(false);

  const groups = useMemo(() => groupBySeverity(findings), [findings]);

  // Counts for the summary header.
  const totalCount = findings.length;
  const decidedCount = Object.keys(decided).length;
  const openCount = totalCount - decidedCount;
  const autoFixableOpen = findings.filter((f) => f.auto_fix_available && !decided[f.id]).length;

  function decide(findingId: string, decision: "accept" | "dismiss", tag: ReasonTag) {
    setDecided((prev) => ({
      ...prev,
      [findingId]: decision === "accept" ? "accepted" : "dismissed",
    }));
    onDecide?.(findingId, decision, tag);
  }

  function autoFix(findingId: string) {
    setDecided((prev) => ({ ...prev, [findingId]: "auto-fixed" }));
    onAutoFix?.(findingId);
  }

  function applyAllAutoFixes() {
    const ids = findings.filter((f) => f.auto_fix_available && !decided[f.id]).map((f) => f.id);
    if (ids.length === 0) return;
    setDecided((prev) => {
      const next = { ...prev };
      for (const id of ids) next[id] = "auto-fixed";
      return next;
    });
    for (const id of ids) onAutoFix?.(id);
  }

  if (findings.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-success/15 text-success">
            ✓
          </div>
          <h3 className="text-sm font-semibold">No findings</h3>
          <p className="mt-1 text-xs text-fg-muted">
            JJSCAN+ surfaced no rule violations against this region.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (openCount === 0) {
    // Everything's been addressed — celebrate.
    return (
      <div className="space-y-4">
        <SummaryHeader
          total={totalCount}
          open={openCount}
          autoFixableOpen={autoFixableOpen}
          showResolved={showResolved}
          onToggleResolved={() => setShowResolved((s) => !s)}
          onApplyAll={applyAllAutoFixes}
        />
        <Card>
          <CardContent className="py-12 text-center">
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-success/15 text-success">
              ✓
            </div>
            <h3 className="text-sm font-semibold">All clear</h3>
            <p className="mt-1 text-xs text-fg-muted">
              All {totalCount} findings addressed. Score should now be{" "}
              {decidedCount > 0 ? "100" : "—"}.
            </p>
          </CardContent>
        </Card>
        {showResolved && <ResolvedList findings={findings} decided={decided} />}
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="findings-list">
      <SummaryHeader
        total={totalCount}
        open={openCount}
        autoFixableOpen={autoFixableOpen}
        showResolved={showResolved}
        onToggleResolved={() => setShowResolved((s) => !s)}
        onApplyAll={applyAllAutoFixes}
      />

      {SEVERITY_ORDER.map((sev) => {
        const items = groups[sev];
        if (items.length === 0) return null;
        const visibleItems = items.filter((f) => showResolved || !decided[f.id]);
        if (visibleItems.length === 0) return null;
        const isCollapsed = collapsed.has(sev);
        return (
          <section
            key={sev}
            className="overflow-hidden rounded-lg border border-border bg-bg-elev"
            data-testid={`severity-group-${sev}`}
          >
            <button
              type="button"
              className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm hover:bg-bg-subtle"
              onClick={() => {
                setCollapsed((prev) => {
                  const next = new Set(prev);
                  if (next.has(sev)) next.delete(sev);
                  else next.add(sev);
                  return next;
                });
              }}
              data-testid={`group-header-${sev}`}
            >
              <span className="flex items-center gap-2">
                <Badge variant={SEVERITY_VARIANT[sev]}>{sev}</Badge>
                <span className="text-fg-muted">
                  {visibleItems.length} finding{visibleItems.length === 1 ? "" : "s"}
                </span>
              </span>
              <span className="text-fg-muted">{isCollapsed ? "▸" : "▾"}</span>
            </button>
            {!isCollapsed && (
              <ul className="divide-y divide-border">
                {visibleItems.map((finding) => (
                  <FindingRow
                    key={finding.id}
                    finding={finding}
                    decidedState={decided[finding.id]}
                    dissent={dissent[finding.rule_id]}
                    expanded={expandedFinding === finding.id}
                    onToggleExpanded={() =>
                      setExpandedFinding((prev) => (prev === finding.id ? null : finding.id))
                    }
                    onAutoFix={autoFix}
                    onAskReason={(decision) => setReasonPicker({ findingId: finding.id, decision })}
                  />
                ))}
              </ul>
            )}
          </section>
        );
      })}

      {reasonPicker && (
        <ReasonPicker
          decision={reasonPicker.decision}
          onCancel={() => setReasonPicker(null)}
          onSubmit={(tag) => {
            decide(reasonPicker.findingId, reasonPicker.decision, tag);
            setReasonPicker(null);
          }}
        />
      )}
    </div>
  );
}

function SummaryHeader({
  total,
  open,
  autoFixableOpen,
  showResolved,
  onToggleResolved,
  onApplyAll,
}: {
  total: number;
  open: number;
  autoFixableOpen: number;
  showResolved: boolean;
  onToggleResolved: () => void;
  onApplyAll: () => void;
}) {
  const resolved = total - open;
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-bg-elev px-4 py-2 text-xs"
      data-testid="findings-summary"
    >
      <div className="flex flex-wrap items-center gap-3">
        <span>
          <strong className="font-semibold text-fg">{open}</strong>{" "}
          <span className="text-fg-muted">open</span>
        </span>
        <span className="text-fg-muted">•</span>
        <span>
          <strong className="font-semibold text-success">{resolved}</strong>{" "}
          <span className="text-fg-muted">resolved</span>
        </span>
        {autoFixableOpen > 0 && (
          <>
            <span className="text-fg-muted">•</span>
            <span>
              <strong className="font-semibold text-accent">{autoFixableOpen}</strong>{" "}
              <span className="text-fg-muted">auto-fixable</span>
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-2">
        {resolved > 0 && (
          <button
            type="button"
            onClick={onToggleResolved}
            className="text-fg-muted underline-offset-4 hover:text-fg hover:underline"
            data-testid="toggle-resolved"
          >
            {showResolved ? "Hide resolved" : `Show resolved (${resolved})`}
          </button>
        )}
        {autoFixableOpen > 0 && (
          <Button size="sm" onClick={onApplyAll} data-testid="apply-all-auto-fixes">
            Apply all {autoFixableOpen} auto-fix{autoFixableOpen === 1 ? "" : "es"}
          </Button>
        )}
      </div>
    </div>
  );
}

function ResolvedList({
  findings,
  decided,
}: {
  findings: Finding[];
  decided: Record<string, DecidedState>;
}) {
  const resolved = findings.filter((f) => decided[f.id]);
  if (resolved.length === 0) return null;
  return (
    <Card>
      <CardContent className="py-3">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fg-muted">
          Resolved ({resolved.length})
        </h3>
        <ul className="space-y-1.5">
          {resolved.map((f) => {
            const state = decided[f.id]!;
            return (
              <li key={f.id} className="flex flex-wrap items-center gap-2 text-xs opacity-70">
                <Badge variant={DECIDED_VARIANT[state]}>{DECIDED_LABEL[state]}</Badge>
                <code className="rounded bg-bg-subtle px-1.5 py-0.5 font-mono">{f.rule_id}</code>
                <span className="line-through">{f.description}</span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

function FindingRow({
  finding,
  decidedState,
  dissent,
  expanded,
  onToggleExpanded,
  onAutoFix,
  onAskReason,
}: {
  finding: Finding;
  decidedState?: DecidedState;
  dissent?: DissentInfo;
  expanded: boolean;
  onToggleExpanded: () => void;
  onAutoFix?: (id: string) => void;
  onAskReason: (decision: "accept" | "dismiss") => void;
}) {
  const dissentVisible =
    dissent && dissent.totalCount > 0 && dissent.dismissedCount / dissent.totalCount >= 0.5;

  const location =
    typeof finding.details?.location === "string"
      ? (finding.details.location as string)
      : undefined;

  const isDecided = Boolean(decidedState);

  return (
    <li
      className={cn("px-4 py-3", isDecided && "opacity-60")}
      data-testid={`finding-${finding.id}`}
      data-rule={finding.rule_id}
      data-decided={decidedState ?? ""}
    >
      {dissentVisible && dissent && !isDecided && (
        <div
          role="alert"
          className="mb-3 flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-xs text-warning"
          data-testid={`dissent-${finding.id}`}
        >
          <span aria-hidden>⚠</span>
          <div>
            <strong className="font-semibold">
              {dissent.dismissedCount} of {dissent.totalCount} teams
            </strong>{" "}
            dismissed this finding on similar jobs
            {dissent.topReason ? ` — top reason: ${dissent.topReason}.` : "."}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <code className="rounded bg-bg-subtle px-1.5 py-0.5 font-mono text-xs">
          {finding.rule_id}
        </code>
        {location && <span className="text-xs text-fg-muted">{location}</span>}
        {decidedState && (
          <Badge variant={DECIDED_VARIANT[decidedState]}>{DECIDED_LABEL[decidedState]}</Badge>
        )}
      </div>

      <p className={cn("mt-2 text-sm", isDecided && "line-through")}>{finding.description}</p>

      <button
        type="button"
        className="mt-1 text-xs text-fg-muted underline-offset-4 hover:text-fg hover:underline"
        onClick={onToggleExpanded}
        data-testid={`expand-${finding.id}`}
      >
        {expanded ? "Hide details" : "Why this matters"}
      </button>
      {expanded && (
        <pre className="mt-2 overflow-x-auto rounded-md bg-bg-subtle p-2 text-xs">
          {JSON.stringify(finding.details ?? {}, null, 2)}
        </pre>
      )}

      {!isDecided && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {finding.auto_fix_available && onAutoFix && (
            <Button
              size="sm"
              onClick={() => onAutoFix(finding.id)}
              data-testid={`autofix-${finding.id}`}
            >
              Apply auto-fix
            </Button>
          )}
          <Button
            size="sm"
            variant="secondary"
            onClick={() => onAskReason("accept")}
            data-testid={`accept-${finding.id}`}
          >
            Accept
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onAskReason("dismiss")}
            data-testid={`dismiss-${finding.id}`}
          >
            Dismiss
          </Button>
        </div>
      )}
    </li>
  );
}

function ReasonPicker({
  decision,
  onCancel,
  onSubmit,
}: {
  decision: "accept" | "dismiss";
  onCancel: () => void;
  onSubmit: (tag: ReasonTag) => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 p-4"
      role="dialog"
      aria-label={`${decision} finding — pick a reason`}
      data-testid="reason-picker"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-sm rounded-lg border border-border bg-bg-elev p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-sm font-semibold capitalize">{decision} reason</h2>
        <p className="mt-1 text-xs text-fg-muted">
          Pick a reason — we record it on the audit log so future scans can surface dissent banners
          on similar findings.
        </p>
        <ul className="mt-3 space-y-1">
          {REASON_TAGS.map((tag) => (
            <li key={tag.value}>
              <button
                type="button"
                onClick={() => onSubmit(tag.value)}
                data-testid={`reason-${tag.value}`}
                className={cn("w-full rounded-md px-3 py-2 text-left text-sm hover:bg-bg-subtle")}
              >
                {tag.label}
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex justify-end">
          <Button size="sm" variant="ghost" onClick={onCancel} data-testid="reason-cancel">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
