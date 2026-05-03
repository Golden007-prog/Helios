"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiRequest } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/keys";

interface RunbookListItem {
  id: string;
  program: string;
  abend_code: string;
  title: string;
  updated_at: string;
}

export default function RunbooksPage() {
  const runbooks = useQuery({
    queryKey: queryKeys.runbooks.list(),
    queryFn: () => apiRequest<{ runbooks: RunbookListItem[] }>("/api/runbooks"),
  });

  return (
    <>
      <PageHeader title="Runbooks" description="Per-program / per-ABEND playbooks." />
      {runbooks.isLoading && <Skeleton className="h-32" />}
      {runbooks.data && runbooks.data.runbooks.length === 0 && (
        <EmptyState Icon={BookOpen} title="No runbooks yet" />
      )}
      <div className="grid gap-3">
        {runbooks.data?.runbooks.map((rb) => (
          <Card key={rb.id}>
            <CardHeader>
              <CardTitle className="text-base">{rb.title}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-fg-muted">
              {rb.program} · {rb.abend_code}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
