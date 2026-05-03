import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RegionTierBadge } from "./region-tier-badge";
import type { RegionListItem } from "@/lib/api/types";

export function RegionCard({ region }: { region: RegionListItem }) {
  return (
    <Link
      href={`/regions/${region.name}`}
      className="block transition-transform hover:-translate-y-0.5"
    >
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <CardTitle>{region.name}</CardTitle>
            <RegionTierBadge tier={region.tier} />
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-y-1 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-fg-muted">HLQ</dt>
              <dd className="font-mono">{region.hlq}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </Link>
  );
}
