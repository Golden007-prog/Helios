"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatRelative } from "@/lib/utils";
import type { QueueItem } from "@/lib/api/types";

export interface QueueCardProps {
  item: QueueItem;
  /** Email of the currently signed-in user. When this matches
   * ``item.initiator`` the card shows a self-review block (Approve /
   * Reject hidden, replaced by a "your request — awaiting reviewer"
   * banner). */
  currentUserEmail?: string;
  /** Optional click handler. Default behaviour is to navigate the user
   * to the underlying artifact when "View diff" is clicked. */
  onViewDiff?: (item: QueueItem) => void;
  onApprove?: (item: QueueItem) => void;
  onReject?: (item: QueueItem) => void;
  /** Highlight this card as the actively-selected one (desktop layout). */
  selected?: boolean;
  /** Click anywhere on the card => select. */
  onSelect?: (item: QueueItem) => void;
}

const STATE_VARIANT: Record<
  QueueItem["state"],
  "neutral" | "low" | "medium" | "critical" | "info" | "high"
> = {
  pending_review: "high",
  approved: "low",
  rejected: "critical",
  auto_approved: "low",
  expired: "info",
};

function summariseReasons(payload: Record<string, unknown>): string[] {
  // Best-effort: payload may carry a top-3 reasons array, or a flat
  // breakdown dict. We accept either and produce up to three labels.
  const reasons: string[] = [];
  if (Array.isArray(payload.top_reasons)) {
    for (const r of payload.top_reasons) {
      if (typeof r === "string") reasons.push(r);
      else if (
        r &&
        typeof r === "object" &&
        "label" in r &&
        typeof (r as { label: unknown }).label === "string"
      ) {
        reasons.push((r as { label: string }).label);
      }
    }
  }
  if (
    reasons.length === 0 &&
    payload.breakdown &&
    typeof payload.breakdown === "object"
  ) {
    const entries = Object.entries(
      payload.breakdown as Record<string, unknown>,
    )
      .filter(([_k, v]) => typeof v === "number" && v > 0)
      .sort((a, b) => Number(b[1]) - Number(a[1]))
      .slice(0, 3)
      .map(([k, v]) => `${k}: −${v}`);
    reasons.push(...entries);
  }
  return reasons.slice(0, 3);
}

export function QueueCard({
  item,
  currentUserEmail,
  onViewDiff,
  onApprove,
  onReject,
  selected,
  onSelect,
}: QueueCardProps) {
  const isSelfReview =
    Boolean(currentUserEmail) && currentUserEmail === item.initiator;
  const reasons = summariseReasons(item.payload);
  const score =
    typeof item.payload.score === "number"
      ? (item.payload.score as number)
      : null;

  return (
    <Card
      data-testid={`queue-card-${item.event_id}`}
      data-self-review={isSelfReview ? "true" : "false"}
      className={cn(
        "transition-colors",
        selected && "ring-2 ring-accent",
        onSelect && "cursor-pointer hover:bg-bg-subtle/40",
      )}
      onClick={onSelect ? () => onSelect(item) : undefined}
    >
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <CardTitle className="text-sm">
            {String(item.payload.jcl ?? item.type)}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={STATE_VARIANT[item.state]}>{item.state}</Badge>
            {score !== null && (
              <Badge
                variant={
                  score >= 80 ? "low" : score >= 60 ? "medium" : "critical"
                }
              >
                score {score}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-muted">
          <span>by {item.initiator}</span>
          <span>{formatRelative(item.created_at)}</span>
        </div>

        {reasons.length > 0 && (
          <ul
            className="mb-3 space-y-1 text-xs"
            data-testid={`queue-reasons-${item.event_id}`}
          >
            {reasons.map((r, i) => (
              <li key={i} className="text-fg-muted">
                • {r}
              </li>
            ))}
          </ul>
        )}

        {isSelfReview ? (
          <div
            className="rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-xs text-warning"
            data-testid={`queue-self-review-${item.event_id}`}
          >
            Your request — awaiting reviewer
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {onApprove && (
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onApprove(item);
                }}
                data-testid={`queue-approve-${item.event_id}`}
              >
                Approve
              </Button>
            )}
            {onViewDiff && (
              <Button
                size="sm"
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewDiff(item);
                }}
                data-testid={`queue-viewdiff-${item.event_id}`}
              >
                View diff
              </Button>
            )}
            {onReject && (
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onReject(item);
                }}
                data-testid={`queue-reject-${item.event_id}`}
              >
                Reject
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
