"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Bug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { analyzeAbend } from "@/lib/api/abend";
import { BANKDEMO_ABENDS } from "@/mocks/bankdemo-samples";

const DEFAULT_SAMPLE = BANKDEMO_ABENDS[0]!;

export default function AbendPage() {
  const router = useRouter();
  const toast = useToast();
  const [syslog, setSyslog] = useState<string>(DEFAULT_SAMPLE.raw_text);
  const [program, setProgram] = useState<string>(DEFAULT_SAMPLE.program);
  const [sampleName, setSampleName] = useState<string>(DEFAULT_SAMPLE.name);

  const analyze = useMutation({
    mutationFn: () => analyzeAbend({ syslog, program: program || undefined }),
    onSuccess: (data) => {
      toast.success("Analysis ready");
      router.push(`/abend/${data.event_id}`);
    },
    onError: (err: Error) => toast.error("Analyze failed", err.message),
  });

  function pickSample(name: string) {
    const sample = BANKDEMO_ABENDS.find((s) => s.name === name);
    if (!sample) return;
    setSampleName(name);
    setSyslog(sample.raw_text);
    setProgram(sample.program);
  }

  return (
    <>
      <PageHeader
        title="ABEND Archaeologist"
        description="Paste a SYSLOG fragment. We pinpoint the failing line and rank root causes."
      />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bug className="size-5 text-accent" /> Analyze a SYSLOG
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
                {BANKDEMO_ABENDS.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} — {s.description}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="program">Program (optional)</Label>
              <Input
                id="program"
                value={program}
                onChange={(e) => setProgram(e.target.value)}
                placeholder="BBANK40P"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="syslog">SYSLOG fragment</Label>
              <Textarea
                id="syslog"
                rows={14}
                value={syslog}
                onChange={(e) => setSyslog(e.target.value)}
                placeholder="IEF450I  S0C7 ..."
                className="font-mono text-xs"
              />
            </div>
            <div className="flex justify-end">
              <Button
                onClick={() => analyze.mutate()}
                disabled={!syslog.trim() || analyze.isPending}
              >
                {analyze.isPending ? "Analyzing…" : "Analyze"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
