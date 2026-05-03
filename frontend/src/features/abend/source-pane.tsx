"use client";

import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface SourcePaneProps {
  programName?: string;
  sourceText: string;
  /** 1-indexed source line that the syslog parser flagged. */
  jumpToLine?: number;
  /** COBOL paragraph the failing instruction is in. */
  paragraphHighlight?: string;
  /** Failing field name (highlighted in green where it appears). */
  fieldHighlight?: string;
  /** Called when "Open in editor" is clicked. */
  onOpenInEditor?: (programName: string) => void;
}

/** Lightweight COBOL-ish syntax colouring. We don't pull in Monaco for this
 * pass — a CSS+span approach gets us the demo-quality view without 1MB
 * of editor weight on the page. */
function lineClasses(
  line: string,
  isJump: boolean,
  inHighlightedParagraph: boolean,
): string {
  return cn(
    "block whitespace-pre px-2 py-px transition-colors",
    isJump
      ? "bg-danger/10 ring-1 ring-danger/40"
      : inHighlightedParagraph
        ? "bg-warning/5"
        : "",
  );
}

/** Render a single line, adding inline highlight spans for the failing
 * field if it appears anywhere in the line. */
function renderInlineField(
  line: string,
  fieldHighlight: string | undefined,
): React.ReactNode {
  if (!fieldHighlight) return line;
  const idx = line.indexOf(fieldHighlight);
  if (idx === -1) return line;
  return (
    <>
      {line.slice(0, idx)}
      <span
        className="rounded bg-success/30 px-0.5 ring-1 ring-success/40"
        data-testid="field-highlight"
      >
        {fieldHighlight}
      </span>
      {line.slice(idx + fieldHighlight.length)}
    </>
  );
}

export function SourcePane({
  programName,
  sourceText,
  jumpToLine,
  paragraphHighlight,
  fieldHighlight,
  onOpenInEditor,
}: SourcePaneProps) {
  const ref = useRef<HTMLDivElement>(null);
  const lines = sourceText.split("\n");

  // Auto-scroll to the jump line on first render / change. ``scrollIntoView``
  // is missing from jsdom; guard so unit tests don't blow up.
  useEffect(() => {
    if (!jumpToLine || !ref.current) return;
    const target = ref.current.querySelector<HTMLElement>(
      `[data-line="${jumpToLine}"]`,
    );
    if (target && typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [jumpToLine]);

  if (!sourceText) {
    return (
      <div
        className="flex h-full flex-col items-center justify-center text-center text-fg-muted"
        data-testid="source-empty"
      >
        <p className="text-sm">No source available</p>
        <p className="mt-1 text-xs">
          The COBOL artifact for this program isn't in the corpus.
        </p>
      </div>
    );
  }

  // Compute paragraph block range — first matching ``XXXX-...`` label and
  // the line before the next label.
  let paragraphStart = -1;
  let paragraphEnd = -1;
  if (paragraphHighlight) {
    const upper = paragraphHighlight.toUpperCase();
    const labelRe = /^\s*(\d{4}-[A-Z][A-Z0-9-]*)\s*\./;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i] ?? "";
      const m = labelRe.exec(line);
      if (m && m[1]) {
        if (paragraphStart === -1 && m[1].toUpperCase() === upper) {
          paragraphStart = i;
        } else if (paragraphStart !== -1 && i > paragraphStart) {
          paragraphEnd = i - 1;
          break;
        }
      }
    }
    if (paragraphStart !== -1 && paragraphEnd === -1) {
      paragraphEnd = lines.length - 1;
    }
  }

  return (
    <div className="flex h-full flex-col" data-testid="source-pane">
      <header className="mb-2 flex items-center justify-between">
        <span className="font-mono text-xs font-semibold">
          {programName ?? "(unnamed source)"}
        </span>
        {programName && onOpenInEditor && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onOpenInEditor(programName)}
          >
            Open in editor
          </Button>
        )}
      </header>
      <div
        ref={ref}
        className="flex-1 overflow-auto rounded-md bg-bg-subtle font-mono text-xs"
      >
        {lines.map((line, i) => {
          const lineNo = i + 1;
          const isJump = lineNo === jumpToLine;
          const inHighlightedParagraph =
            paragraphStart !== -1 &&
            lineNo - 1 >= paragraphStart &&
            lineNo - 1 <= paragraphEnd;
          return (
            <div
              key={i}
              data-line={lineNo}
              data-testid={isJump ? "jump-line" : undefined}
              className={lineClasses(line, isJump, inHighlightedParagraph)}
            >
              <span className="mr-3 inline-block w-10 text-right text-fg-muted/70">
                {lineNo}
              </span>
              {renderInlineField(line, fieldHighlight)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
