"use client";

import { useParams } from "next/navigation";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageHeader } from "@/components/ui/page-header";
import { BobStub } from "@/components/ui/bob-stub";

/**
 * Three-pane layout. Page shell + panel divs + resize handles are here; the
 * contents of each pane are Bob's per docs/PHASE_PLAN.md §1.4.
 */
export default function AbendDetailPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <Breadcrumbs
        items={[{ label: "ABEND Archaeologist", href: "/abend" }, { label: id }]}
      />
      <PageHeader title="ABEND analysis" />
      <div className="grid h-[70vh] grid-cols-1 gap-4 lg:grid-cols-[1fr_1fr_1fr]">
        <ResizablePane label="SYSLOG fragment">
          {/* BOB: hero-shot SYSLOG parser feedback per docs/PHASE_PLAN.md §1.4 */}
          <BobStub
            feature="SYSLOG parser feedback"
            spec="Highlight what was extracted (program, paragraph, ABEND code, offsets). Click-to-copy."
          />
        </ResizablePane>
        <ResizablePane label="Source view">
          {/* BOB: hero-shot Monaco source view that jumps to the failing line */}
          <BobStub
            feature="Source view"
            spec="Monaco read-only, jumps to the failing line, highlights paragraph + field referenced in the ABEND."
          />
        </ResizablePane>
        <ResizablePane label="Analysis">
          {/* BOB: hero-shot ranked root causes + matching runbooks + tier banner */}
          <BobStub
            feature="Analysis pane"
            spec="Identified ABEND, confidence tier banner (confirmed | probable | unfamiliar | unknown), ranked root causes, matching runbooks, one-click 'Apply quarantine SQL' gated by confirmed."
          />
        </ResizablePane>
      </div>
    </>
  );
}

function ResizablePane({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
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
