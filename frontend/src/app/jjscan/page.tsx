"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Scan } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { submitScan } from "@/lib/api/jjscan";
import { listRegions } from "@/lib/api/regions";
import { queryKeys } from "@/lib/api/keys";

export default function JjscanPage() {
  const router = useRouter();
  const toast = useToast();
  const [source, setSource] = useState("");
  const [region, setRegion] = useState("int3");

  const regions = useQuery({
    queryKey: queryKeys.regions.list(),
    queryFn: () => listRegions(),
  });

  const submit = useMutation({
    mutationFn: () => submitScan({ jcl_source: source, target_region: region }),
    onSuccess: (data) => {
      toast.success("Scan submitted");
      router.push(`/jjscan/${data.job_id}`);
    },
    onError: (err: Error) => toast.error("Submit failed", err.message),
  });

  return (
    <>
      <PageHeader
        title="JJSCAN+"
        description="Static JCL analysis for the four seeded rules."
      />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scan className="size-5 text-accent" /> Submit a scan
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="region">Target region</Label>
              <select
                id="region"
                className="h-9 w-full rounded-md border border-border bg-bg-elev px-3 text-sm"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              >
                {regions.data?.regions.map((r) => (
                  <option key={r.name} value={r.name}>
                    {r.name} ({r.tier})
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="source">JCL source</Label>
              <Textarea
                id="source"
                rows={14}
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="//FOO    JOB ..."
              />
            </div>
            <div className="flex justify-end">
              <Button
                onClick={() => submit.mutate()}
                disabled={!source.trim() || submit.isPending}
              >
                {submit.isPending ? "Submitting…" : "Run scan"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
