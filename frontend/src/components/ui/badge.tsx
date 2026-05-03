import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        neutral: "bg-bg-subtle text-fg",
        critical: "bg-danger/15 text-danger",
        high: "bg-warning/15 text-warning",
        medium: "bg-accent/15 text-accent",
        low: "bg-success/15 text-success",
        info: "bg-bg-subtle text-fg-muted",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
