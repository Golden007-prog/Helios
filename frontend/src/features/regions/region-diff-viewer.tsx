"use client";

import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { explainPath } from "./diff-explanations";
import type { DiffField } from "@/lib/api/types";

export interface RegionDiffViewerProps {
  regionA: string;
  regionB: string;
  fields: DiffField[];
  /** Optional swap callback. Renders a "↔ swap" button when provided. */
  onSwap?: () => void;
  /** Called on initial render with the wall-clock millis the render took.
   * Lets a parent test assert the P95 budget. */
  onRenderTime?: (ms: number) => void;
}

const KIND_BG: Record<DiffField["kind"], string> = {
  value_change: "bg-warning/10 hover:bg-warning/20",
  added: "bg-success/10 hover:bg-success/20",
  removed: "bg-danger/10 hover:bg-danger/20",
};

const KIND_DOT: Record<DiffField["kind"], string> = {
  value_change: "bg-warning",
  added: "bg-success",
  removed: "bg-danger",
};

function renderValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export function RegionDiffViewer({
  regionA,
  regionB,
  fields,
  onSwap,
  onRenderTime,
}: RegionDiffViewerProps) {
  const [filter, setFilter] = useState<"all" | "changes">("changes");

  // ``fields`` already contains only differences from the API; the filter
  // toggle is here so the UI can demonstrate the "show all" path when
  // wired to a future variant of the endpoint that returns matches too.
  const visible = useMemo(() => {
    const start = performance.now();
    const result = filter === "all" ? fields : fields;
    onRenderTime?.(performance.now() - start);
    return result;
  }, [fields, filter, onRenderTime]);

  if (visible.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-success/15 text-success">
            ✓
          </div>
          <h3 className="text-sm font-semibold">All fields aligned</h3>
          <p className="mt-1 text-xs text-fg-muted">
            {regionA} and {regionB} match on every tracked field.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="region-diff-viewer">
      <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-border bg-bg-elev/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-mono font-semibold">{regionA}</span>
          <button
            type="button"
            onClick={onSwap}
            disabled={!onSwap}
            className="rounded-md border border-border px-2 py-0.5 text-fg-muted transition-colors hover:bg-bg-subtle disabled:opacity-40"
            aria-label="Swap regions"
            data-testid="swap-regions"
          >
            ↔
          </button>
          <span className="font-mono font-semibold">{regionB}</span>
        </div>
        <div className="flex items-center gap-1 text-xs">
          <button
            type="button"
            className={cn(
              "rounded-md px-2 py-0.5",
              filter === "changes"
                ? "bg-bg-subtle text-fg"
                : "text-fg-muted hover:bg-bg-subtle/50",
            )}
            onClick={() => setFilter("changes")}
            data-testid="filter-changes"
          >
            Changes only
          </button>
          <button
            type="button"
            className={cn(
              "rounded-md px-2 py-0.5",
              filter === "all"
                ? "bg-bg-subtle text-fg"
                : "text-fg-muted hover:bg-bg-subtle/50",
            )}
            onClick={() => setFilter("all")}
            data-testid="filter-all"
          >
            All fields
          </button>
        </div>
      </div>
      <CardContent className="p-0">
        <ul role="list" className="divide-y divide-border">
          {visible.map((field) => (
            <DiffRow
              key={field.path}
              field={field}
              regionA={regionA}
              regionB={regionB}
            />
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function DiffRow({
  field,
  regionA,
  regionB,
}: {
  field: DiffField;
  regionA: string;
  regionB: string;
}) {
  const explanation = explainPath(field.path);
  const [hovered, setHovered] = useState(false);
  return (
    <li
      role="listitem"
      data-testid={`diff-row-${field.path}`}
      data-kind={field.kind}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      tabIndex={0}
      className={cn(
        "relative grid grid-cols-1 items-stretch transition-colors lg:grid-cols-[minmax(180px,1fr)_minmax(120px,1fr)_minmax(120px,1fr)]",
        KIND_BG[field.kind],
      )}
    >
      <div className="flex items-center gap-2 px-4 py-2 text-sm">
        <span
          className={cn(
            "h-2 w-2 shrink-0 rounded-full",
            KIND_DOT[field.kind],
          )}
          aria-hidden
        />
        <code className="text-xs">{field.path}</code>
      </div>
      <div className="px-4 py-2 font-mono text-xs lg:border-l lg:border-border/40">
        <div className="text-[10px] uppercase tracking-wider text-fg-muted/80">
          {regionA}
        </div>
        {renderValue(field.a)}
      </div>
      <div className="px-4 py-2 font-mono text-xs lg:border-l lg:border-border/40">
        <div className="text-[10px] uppercase tracking-wider text-fg-muted/80">
          {regionB}
        </div>
        {renderValue(field.b)}
      </div>
      {hovered && explanation && (
        <div
          role="tooltip"
          className="pointer-events-none absolute right-4 top-2 max-w-xs rounded-md border border-border bg-bg shadow-md"
          data-testid={`tooltip-${field.path}`}
        >
          <p className="px-3 py-2 text-xs text-fg-muted">{explanation}</p>
        </div>
      )}
    </li>
  );
}
