"use client";

import { useMemo } from "react";

/**
 * Read-only JCL viewer with column-72 ruler. Intentionally text-only — Bob
 * is expected to swap in Monaco for the real diff/edit experience in the
 * hero shot pages.
 */
export function JclViewer({ source }: { source: string }) {
  const lines = useMemo(() => source.split(/\r?\n/), [source]);
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-bg-elev font-mono text-xs">
      <table className="w-full">
        <tbody>
          {lines.map((line, i) => (
            <tr key={i}>
              <td className="select-none border-r border-border bg-bg-subtle px-2 py-0.5 text-right text-fg-muted">
                {(i + 1).toString().padStart(4, " ")}
              </td>
              <td className="whitespace-pre px-3 py-0.5">{line}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
