"use client";

import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ParserHighlight } from "./types";

export interface SyslogPaneProps {
  rawText: string;
  parserHighlights?: ParserHighlight[];
  /** Called when the user clicks a highlighted span. Lets the source pane
   * jump to the matching location. */
  onSelect?: (kind: ParserHighlight["kind"], value: string) => void;
  /** Optional callback when the "Copy raw" button is clicked. The default
   * uses ``navigator.clipboard``. */
  onCopy?: () => void;
}

const KIND_CLASS: Record<ParserHighlight["kind"], string> = {
  abend_code: "bg-danger/20 text-danger ring-1 ring-danger/30",
  program: "bg-accent/20 text-accent ring-1 ring-accent/30",
  paragraph: "bg-warning/20 text-warning ring-1 ring-warning/30",
  field: "bg-success/20 text-success ring-1 ring-success/30",
  step: "bg-bg-subtle ring-1 ring-border",
};

/** Slice the raw text into a list of {text, kind?} fragments, sorted by
 * offset, with no overlap. Highlights that overlap are merged onto the
 * earliest one. */
function sliceWithHighlights(
  raw: string,
  highlights: ParserHighlight[],
): { text: string; highlight?: ParserHighlight }[] {
  if (highlights.length === 0) return [{ text: raw }];
  const sorted = [...highlights].sort((a, b) => a.offset - b.offset);
  const result: { text: string; highlight?: ParserHighlight }[] = [];
  let cursor = 0;
  for (const h of sorted) {
    if (h.offset < cursor) continue; // overlap → skip
    if (h.offset > cursor) {
      result.push({ text: raw.slice(cursor, h.offset) });
    }
    result.push({ text: raw.slice(h.offset, h.offset + h.length), highlight: h });
    cursor = h.offset + h.length;
  }
  if (cursor < raw.length) {
    result.push({ text: raw.slice(cursor) });
  }
  return result;
}

export function SyslogPane({
  rawText,
  parserHighlights = [],
  onSelect,
  onCopy,
}: SyslogPaneProps) {
  const fragments = useMemo(
    () => sliceWithHighlights(rawText, parserHighlights),
    [rawText, parserHighlights],
  );

  if (!rawText) {
    return (
      <div
        className="flex h-full flex-col items-center justify-center text-center text-fg-muted"
        data-testid="syslog-empty"
      >
        <p className="text-sm">Paste your SYSLOG to begin</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col" data-testid="syslog-pane">
      <header className="mb-2 flex items-center justify-end gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            if (onCopy) {
              onCopy();
              return;
            }
            navigator.clipboard?.writeText(rawText).catch(() => {});
          }}
        >
          Copy raw
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            const blob = new Blob([rawText], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "abend.txt";
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          Download
        </Button>
      </header>
      <pre
        className="flex-1 overflow-auto whitespace-pre-wrap rounded-md bg-bg-subtle p-3 font-mono text-xs"
        data-testid="syslog-content"
      >
        {fragments.map((f, idx) =>
          f.highlight ? (
            <button
              key={idx}
              type="button"
              onClick={() => onSelect?.(f.highlight!.kind, f.highlight!.value)}
              className={cn(
                "rounded px-0.5 transition-colors hover:opacity-80",
                KIND_CLASS[f.highlight.kind],
              )}
              data-testid={`hl-${f.highlight.kind}-${f.highlight.value}`}
              data-kind={f.highlight.kind}
            >
              {f.text}
            </button>
          ) : (
            <span key={idx}>{f.text}</span>
          ),
        )}
      </pre>
    </div>
  );
}
