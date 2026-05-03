"use client";

import { useCallback, useState } from "react";
import { Inbox } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { QueueCard } from "@/features/queue/queue-card";
import { useReviewQueue } from "@/features/queue/use-review-queue";
import { fetchMe } from "@/lib/api/auth";
import { approveQueueItem, rejectQueueItem } from "@/lib/api/queue";
import { queryKeys } from "@/lib/api/keys";
import type { QueueItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const CONNECTION_LABEL: Record<
  ReturnType<typeof useReviewQueue>["connection"],
  { text: string; classes: string }
> = {
  live: { text: "Live", classes: "bg-success/15 text-success" },
  connecting: { text: "Connecting…", classes: "bg-bg-subtle text-fg-muted" },
  polling: { text: "Polling", classes: "bg-warning/15 text-warning" },
  offline: { text: "Offline", classes: "bg-danger/15 text-danger" },
};

export default function ReviewPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const me = useQuery({
    queryKey: queryKeys.auth.me(),
    queryFn: fetchMe,
    staleTime: Infinity,
  });
  const myEmail = me.data?.user.email;

  const onNewPending = useCallback(
    (eventId: string) => {
      toast.show({
        variant: "default",
        title: "New pending review",
        description: `Event ${eventId.slice(0, 12)} needs your decision.`,
      });
    },
    [toast],
  );

  const queue = useReviewQueue({ onNewPending });

  const approve = useMutation({
    mutationFn: (item: QueueItem) => approveQueueItem(item.event_id),
    onSuccess: (_data, item) => {
      toast.success("Approved", `${item.payload.jcl ?? item.type}`);
      queryClient.invalidateQueries({ queryKey: queryKeys.queue.list() });
    },
    onError: (e) => toast.error("Approve failed", (e as Error).message),
  });
  const reject = useMutation({
    mutationFn: (item: QueueItem) =>
      rejectQueueItem(item.event_id, "Rejected via review queue"),
    onSuccess: (_data, item) => {
      toast.success("Rejected", `${item.payload.jcl ?? item.type}`);
      queryClient.invalidateQueries({ queryKey: queryKeys.queue.list() });
    },
    onError: (e) => toast.error("Reject failed", (e as Error).message),
  });

  const selected = queue.items.find((i) => i.event_id === selectedId) ?? null;

  return (
    <>
      <PageHeader
        title="Review Queue"
        description="Real-time approvals with mobile-responsive layout."
        action={
          <span
            data-testid="connection-indicator"
            className={cn(
              "rounded-md px-2 py-0.5 text-xs font-medium",
              CONNECTION_LABEL[queue.connection].classes,
            )}
          >
            {CONNECTION_LABEL[queue.connection].text}
          </span>
        }
      />

      {queue.isLoading && <Skeleton className="h-32" />}

      {!queue.isLoading && queue.items.length === 0 && (
        <EmptyState
          Icon={Inbox}
          title="Queue is empty"
          description="Nothing pending review."
        />
      )}

      {queue.items.length > 0 && (
        <div
          // Mobile (default): single column. Desktop (lg+): two-column with
          // the detail pane on the right.
          className="grid grid-cols-1 gap-4 pb-24 lg:grid-cols-[minmax(280px,1fr)_minmax(320px,2fr)] lg:pb-0"
          data-testid="queue-layout"
        >
          <ul
            role="list"
            className="space-y-3"
            data-testid="queue-list"
          >
            {queue.items.map((item) => (
              <li key={item.event_id}>
                <QueueCard
                  item={item}
                  currentUserEmail={myEmail}
                  selected={selectedId === item.event_id}
                  onSelect={(it) => setSelectedId(it.event_id)}
                  onApprove={(it) => approve.mutate(it)}
                  onReject={(it) => reject.mutate(it)}
                  onViewDiff={(it) => {
                    if (typeof it.payload.jcl === "string") {
                      window.location.href = `/jjscan/${encodeURIComponent(
                        String(it.payload.jcl),
                      )}`;
                    }
                  }}
                />
              </li>
            ))}
          </ul>

          <aside
            className="hidden lg:block"
            data-testid="queue-detail-pane"
            aria-live="polite"
          >
            {selected ? (
              <Card>
                <CardContent className="space-y-3 py-4">
                  <h3 className="text-sm font-semibold">Event detail</h3>
                  <dl className="grid grid-cols-3 gap-x-3 gap-y-1 text-xs">
                    <dt className="text-fg-muted">Type</dt>
                    <dd className="col-span-2">{selected.type}</dd>
                    <dt className="text-fg-muted">Initiator</dt>
                    <dd className="col-span-2">{selected.initiator}</dd>
                    <dt className="text-fg-muted">State</dt>
                    <dd className="col-span-2">
                      <Badge>{selected.state}</Badge>
                    </dd>
                  </dl>
                  <pre className="overflow-x-auto rounded-md bg-bg-subtle p-2 text-xs">
                    {JSON.stringify(selected.payload, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-xs text-fg-muted">
                  Select an event to see its detail.
                </CardContent>
              </Card>
            )}
          </aside>
        </div>
      )}

      {/* Mobile sticky action bar — only renders when an event is selected. */}
      {selected && !selected.initiator.includes(myEmail ?? "@") && (
        <div
          data-testid="mobile-action-bar"
          className="fixed bottom-0 left-0 right-0 z-30 border-t border-border bg-bg-elev p-3 lg:hidden"
        >
          <div className="mx-auto flex max-w-screen-sm gap-2">
            <Button
              size="sm"
              className="flex-1"
              onClick={() => approve.mutate(selected)}
              data-testid="mobile-approve"
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="flex-1"
              onClick={() => reject.mutate(selected)}
              data-testid="mobile-reject"
            >
              Reject
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
