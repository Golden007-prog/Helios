"use client";

import { useQuery } from "@tanstack/react-query";
import { Inbox } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { listQueue } from "@/lib/api/queue";
import { queryKeys } from "@/lib/api/keys";
import { formatRelative } from "@/lib/utils";

export default function ReviewPage() {
  const queue = useQuery({
    queryKey: queryKeys.queue.list(),
    queryFn: () => listQueue(),
    refetchInterval: 5000,
  });

  return (
    <>
      <PageHeader
        title="Review Queue"
        description="Real-time approvals with mobile-responsive layout."
      />

      {queue.isLoading && <Skeleton className="h-32" />}

      {queue.data && queue.data.items.length === 0 && (
        <EmptyState Icon={Inbox} title="Queue is empty" description="Nothing pending review." />
      )}

      <div className="grid gap-3">
        {queue.data?.items.map((item) => (
          <Card key={item.event_id}>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <CardTitle className="text-sm">
                  {String(item.payload.jcl ?? item.type)}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge>{item.state}</Badge>
                  {typeof item.payload.score === "number" && (
                    <Badge variant="medium">score {item.payload.score}</Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-fg-muted">
                <span>by {item.initiator}</span>
                <span>{formatRelative(item.created_at)}</span>
              </div>
              <div className="flex gap-2">
                <Button size="sm">Approve</Button>
                <Button size="sm" variant="secondary">
                  View diff
                </Button>
                <Button size="sm" variant="ghost">
                  Reject
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
