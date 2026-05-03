import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Visual placeholder for hero-feature components Bob owns. Renders the spec
 * inline so reviewers know exactly what's missing without grepping the
 * source tree.
 */
interface BobStubProps {
  feature: string;
  spec: string;
  className?: string;
}

export function BobStub({ feature, spec, className }: BobStubProps) {
  return (
    <div
      className={cn(
        "rounded-lg border-2 border-dashed border-accent/40 bg-accent/5 p-6",
        className,
      )}
      data-bob-stub="true"
      data-feature={feature}
    >
      <div className="flex items-center gap-2 text-sm font-semibold text-accent">
        <Sparkles className="size-4" />
        BOB: {feature} coming soon
      </div>
      <p className="mt-2 max-w-2xl text-sm text-fg-muted">{spec}</p>
    </div>
  );
}
