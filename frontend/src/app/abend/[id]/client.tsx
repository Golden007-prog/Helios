"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { AnalysisPane } from "@/features/abend/analysis-pane";
import { SourcePane } from "@/features/abend/source-pane";
import { SyslogPane } from "@/features/abend/syslog-pane";
import type { AbendAnalysisResponse, ParserHighlight } from "@/features/abend/types";
import { apiRequest } from "@/lib/api/client";
import { resolveAbend } from "@/lib/api/abend";
import { queryKeys } from "@/lib/api/keys";

interface AbendDetailDoc extends AbendAnalysisResponse {
  raw_text?: string;
  source_text?: string;
}

function buildHighlights(raw: string, abend: AbendAnalysisResponse): ParserHighlight[] {
  const out: ParserHighlight[] = [];
  const seen = new Set<string>();
  const push = (value: string | null | undefined, kind: ParserHighlight["kind"]) => {
    if (!value) return;
    const idx = raw.indexOf(value);
    if (idx === -1) return;
    const key = `${kind}:${idx}:${value}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ offset: idx, length: value.length, kind, value });
  };
  push(abend.identified_abend.code, "abend_code");
  push(abend.failing_step.program, "program");
  push(abend.failing_step.step_name, "step");
  push(abend.source_trace.paragraph, "paragraph");
  push(abend.source_trace.highlighted_field, "field");
  return out.sort((a, b) => a.offset - b.offset);
}

export default function AbendDetailClient({ id }: { id: string }) {
  const [jumpLine, setJumpLine] = useState<number | undefined>(undefined);
  const toast = useToast();

  const event = useQuery({
    queryKey: queryKeys.abend.detail(id),
    queryFn: () => apiRequest<AbendDetailDoc>(`/api/abend/${encodeURIComponent(id)}`),
  });

  const resolve = useMutation({
    mutationFn: (note: string) =>
      resolveAbend(id, { fix: note, runbook: "rb-cobol-s0c7-handling" }),
    onSuccess: () => toast.success("Resolution recorded", "Audit + learning event written"),
    onError: (err: Error) => toast.error("Resolve failed", err.message ?? "Unknown error"),
  });

  const highlights = useMemo(
    () => (event.data?.raw_text ? buildHighlights(event.data.raw_text, event.data) : []),
    [event.data],
  );

  return (
    <>
      <Breadcrumbs items={[{ label: "ABEND Archaeologist", href: "/abend" }, { label: id }]} />
      <PageHeader title="ABEND analysis" />
      {event.isLoading && <Skeleton className="h-[70vh]" />}
      {event.data && (
        <div className="grid h-[70vh] grid-cols-1 gap-4 lg:grid-cols-[1fr_1fr_1fr]">
          <ResizablePane label="SYSLOG fragment">
            <SyslogPane
              rawText={event.data.raw_text ?? ""}
              parserHighlights={highlights}
              onSelect={(kind, _value) => {
                if (kind === "paragraph" && event.data?.source_trace.line) {
                  setJumpLine(event.data.source_trace.line);
                }
              }}
            />
          </ResizablePane>
          <ResizablePane label="Source view">
            <SourcePane
              programName={event.data.failing_step.program ?? undefined}
              sourceText={event.data.source_text ?? ""}
              jumpToLine={jumpLine ?? event.data.source_trace.line ?? undefined}
              paragraphHighlight={event.data.source_trace.paragraph ?? undefined}
              fieldHighlight={event.data.source_trace.highlighted_field ?? undefined}
            />
          </ResizablePane>
          <ResizablePane label="Analysis">
            <AnalysisPane
              abend={event.data}
              onSubmitResolution={(text) => resolve.mutate(text)}
              onApplyQuarantine={(sql) => {
                navigator.clipboard?.writeText(sql).catch(() => {});
                toast.success("Quarantine SQL copied", "Paste into your DB2 console");
              }}
              onSubmitPattern={() => {
                toast.show({
                  variant: "default",
                  title: "Pattern submitted",
                  description: "Will appear in the learning loop next run",
                });
              }}
            />
          </ResizablePane>
        </div>
      )}
    </>
  );
}

function ResizablePane({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section
      aria-label={label}
      className="flex min-h-0 flex-col rounded-lg border border-border bg-bg-elev"
    >
      <header className="flex items-center justify-between border-b border-border px-3 py-2 text-xs font-medium text-fg-muted">
        <span>{label}</span>
        <span className="cursor-col-resize select-none text-fg-muted/60">⇔</span>
      </header>
      <div className="flex-1 overflow-auto p-3">{children}</div>
    </section>
  );
}
