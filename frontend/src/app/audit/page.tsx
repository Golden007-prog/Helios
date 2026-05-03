"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/keys";
import { formatRelative } from "@/lib/utils";
import type { ColumnDef } from "@tanstack/react-table";

interface AuditEntry {
  id: string;
  type: string;
  actor: string;
  created_at: string;
  subject: { kind: string; name: string };
}

const columns: ColumnDef<AuditEntry>[] = [
  { accessorKey: "type", header: "Type", cell: (c) => <Badge>{String(c.getValue())}</Badge> },
  { accessorKey: "actor", header: "Actor" },
  {
    id: "subject",
    header: "Subject",
    cell: (c) => {
      const s = c.row.original.subject;
      return (
        <span className="font-mono text-xs">
          {s.kind}:{s.name}
        </span>
      );
    },
  },
  {
    accessorKey: "created_at",
    header: "When",
    cell: (c) => formatRelative(String(c.getValue())),
  },
];

export default function AuditPage() {
  const data = useQuery({
    queryKey: queryKeys.audit.list(),
    queryFn: () => apiRequest<{ items: AuditEntry[]; bookmark: string | null }>("/api/audit"),
  });

  return (
    <>
      <PageHeader title="Audit Log" description="Hash-chained, query-grade." />
      {data.isLoading && <Skeleton className="h-48" />}
      {data.data && (
        <DataTable
          columns={columns}
          data={data.data.items}
          empty={<EmptyState Icon={FileText} title="No audit entries yet" />}
        />
      )}
    </>
  );
}
