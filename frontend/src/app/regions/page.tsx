"use client";

import { useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Plus, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { listRegions, upsertRegion } from "@/lib/api/regions";
import { queryKeys } from "@/lib/api/keys";
import { RegionCard } from "@/features/regions/region-card";
import { RegionForm } from "@/features/regions/region-form";

export default function RegionsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [open, setOpen] = useState(false);

  const regions = useQuery({
    queryKey: queryKeys.regions.list(),
    queryFn: () => listRegions(),
  });

  const create = useMutation({
    mutationFn: async (values: {
      name: string;
      tier: "sandbox" | "development" | "integration" | "production";
      hlq: string;
      db2_subsystem: string;
      db2_plan_collection: string;
      racf_group?: string;
      scheduler_queue?: string;
      reason: string;
    }) =>
      upsertRegion(
        values.name,
        {
          name: values.name,
          tier: values.tier,
          hlq: values.hlq,
          db2: {
            subsystem_id: values.db2_subsystem,
            plan_collection: values.db2_plan_collection,
          },
          racf_group: values.racf_group ?? null,
          scheduler_queue: values.scheduler_queue ?? null,
        },
        values.reason,
      ),
    onSuccess: () => {
      toast.success("Region saved");
      qc.invalidateQueries({ queryKey: queryKeys.regions.all() });
      setOpen(false);
    },
    onError: (err: Error) => toast.error("Save failed", err.message),
  });

  return (
    <>
      <PageHeader
        title="Region Atlas"
        description="Versioned profiles for sandbox, dev, int, prod, dr."
        action={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="size-4" /> New region
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create region</DialogTitle>
              </DialogHeader>
              <RegionForm
                onSubmit={async (values) => {
                  await create.mutateAsync(values);
                }}
                submitLabel="Create"
              />
            </DialogContent>
          </Dialog>
        }
      />

      {regions.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      )}

      {regions.isError && (
        <EmptyState
          Icon={Globe}
          title="Couldn't load regions"
          description={(regions.error as Error).message}
          action={
            <Button onClick={() => regions.refetch()} variant="secondary" size="sm">
              Retry
            </Button>
          }
        />
      )}

      {regions.data && regions.data.regions.length === 0 && (
        <EmptyState
          Icon={Globe}
          title="No regions yet"
          description="Seed the corpus or create one above."
        />
      )}

      {regions.data && regions.data.regions.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {regions.data.regions.map((r) => (
            <RegionCard key={r.name} region={r} />
          ))}
        </div>
      )}
    </>
  );
}
