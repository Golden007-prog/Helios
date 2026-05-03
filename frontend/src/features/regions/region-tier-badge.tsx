import { Badge } from "@/components/ui/badge";
import type { RegionTier } from "@/lib/api/types";

const VARIANT: Record<RegionTier, "info" | "low" | "medium" | "critical"> = {
  sandbox: "info",
  development: "low",
  integration: "medium",
  production: "critical",
};

export function RegionTierBadge({ tier }: { tier: RegionTier }) {
  return <Badge variant={VARIANT[tier]}>{tier}</Badge>;
}
