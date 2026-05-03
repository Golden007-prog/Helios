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
import { BANKDEMO_JCLS } from "@/mocks/bankdemo-samples";

const DEFAULT_SAMPLE = BANKDEMO_JCLS[0]!;

export default function JjscanPage() {
  const router = useRouter();
  const toast = useToast();
  const [source, setSource] = useState<string>(DEFAULT_SAMPLE.source);
  const [sampleName, setSampleName] = useState<string>(DEFAULT_SAMPLE.name);
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

  function pickSample(name: string) {
    const sample = BANKDEMO_JCLS.find((s) => s.name === name);
    if (!sample) return;
    setSampleName(name);
    setSource(sample.source);
  }

  return (
    <>
      <PageHeader title="JJSCAN+" description="Static JCL analysis for the four seeded rules." />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scan className="size-5 text-accent" /> Submit a scan
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="sample">BankDemo sample (optional)</Label>
              <select
                id="sample"
                className="h-9 w-full rounded-md border border-border bg-bg-elev px-3 text-sm"
                value={sampleName}
                onChange={(e) => pickSample(e.target.value)}
              >
                {BANKDEMO_JCLS.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} — {s.description}
                  </option>
                ))}
              </select>
              <p className="text-xs text-fg-muted">
                Real JCL pulled from the Rocket BankDemo corpus. Edit the textarea to scan your own.
              </p>
            </div>
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
                className="font-mono text-xs"
              />
            </div>
            <div className="flex justify-end">
              <Button onClick={() => submit.mutate()} disabled={!source.trim() || submit.isPending}>
                {submit.isPending ? "Submitting…" : "Run scan"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
