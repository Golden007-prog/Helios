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

export default function AbendPage() {
  const router = useRouter();
  const toast = useToast();
  const [syslog, setSyslog] = useState("");
  const [program, setProgram] = useState("");

  const analyze = useMutation({
    mutationFn: () => analyzeAbend({ syslog, program: program || undefined }),
    onSuccess: (data) => {
      toast.success("Analysis ready");
      router.push(`/abend/${data.event_id}`);
    },
    onError: (err: Error) => toast.error("Analyze failed", err.message),
  });

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
              <Label htmlFor="program">Program (optional)</Label>
              <Input
                id="program"
                value={program}
                onChange={(e) => setProgram(e.target.value)}
                placeholder="CUSTPROC"
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
