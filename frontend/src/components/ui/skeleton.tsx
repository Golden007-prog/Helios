import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-bg-subtle", className)}
      role="status"
      aria-label="Loading"
      {...props}
    />
  );
}
