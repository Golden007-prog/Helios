"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import type { RegionProfile, RegionTier } from "@/lib/api/types";

const TIERS: RegionTier[] = ["sandbox", "development", "integration", "production"];

const schema = z.object({
  name: z.string().min(1).max(64),
  tier: z.enum(["sandbox", "development", "integration", "production"]),
  hlq: z.string().min(1),
  db2_subsystem: z.string().min(1),
  db2_plan_collection: z.string().min(1),
  racf_group: z.string().optional(),
  scheduler_queue: z.string().optional(),
  reason: z.string().min(3).max(400),
});

export type RegionFormValues = z.infer<typeof schema>;

interface Props {
  initial?: Partial<RegionProfile>;
  onSubmit: (values: RegionFormValues) => Promise<void> | void;
  submitLabel?: string;
}

export function RegionForm({ initial, onSubmit, submitLabel = "Save" }: Props) {
  const form = useForm<RegionFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initial?.name ?? "",
      tier: initial?.tier ?? "development",
      hlq: initial?.hlq ?? "",
      db2_subsystem: initial?.db2?.subsystem_id ?? "",
      db2_plan_collection: initial?.db2?.plan_collection ?? "",
      racf_group: initial?.racf_group ?? "",
      scheduler_queue: initial?.scheduler_queue ?? "",
      reason: "",
    },
  });

  return (
    <form
      onSubmit={form.handleSubmit(async (values) => onSubmit(values))}
      className="grid gap-4 sm:grid-cols-2"
    >
      <div className="grid gap-1.5">
        <Label htmlFor="name">Name</Label>
        <Input id="name" {...form.register("name")} disabled={Boolean(initial?.name)} />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="tier">Tier</Label>
        <select
          id="tier"
          {...form.register("tier")}
          className="h-9 rounded-md border border-border bg-bg-elev px-3 text-sm"
        >
          {TIERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-1.5 sm:col-span-2">
        <Label htmlFor="hlq">High-level qualifier</Label>
        <Input id="hlq" {...form.register("hlq")} placeholder="PROD.INT3" />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="db2_subsystem">DB2 subsystem id</Label>
        <Input id="db2_subsystem" {...form.register("db2_subsystem")} placeholder="DB2I" />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="db2_plan_collection">DB2 plan collection</Label>
        <Input
          id="db2_plan_collection"
          {...form.register("db2_plan_collection")}
          placeholder="INT3.COLL"
        />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="racf_group">RACF group</Label>
        <Input id="racf_group" {...form.register("racf_group")} placeholder="BANKAPP" />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="scheduler_queue">Scheduler queue</Label>
        <Input id="scheduler_queue" {...form.register("scheduler_queue")} />
      </div>
      <div className="grid gap-1.5 sm:col-span-2">
        <Label htmlFor="reason">Reason for change</Label>
        <Input id="reason" {...form.register("reason")} placeholder="Describe why" />
        {form.formState.errors.reason && (
          <p className="text-xs text-danger">{form.formState.errors.reason.message}</p>
        )}
      </div>
      <div className="flex justify-end sm:col-span-2">
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
