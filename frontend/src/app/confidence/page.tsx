import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BobStub } from "@/components/ui/bob-stub";

export default function ConfidencePage() {
  return (
    <>
      <PageHeader
        title="Confidence Score"
        description="0–100 readiness wrapper composed from JJSCAN+ findings, region mismatch, backup-gap, and historical ABEND priors."
      />
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>How it composes</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            <li>Severity-weighted JJSCAN+ deductions (per-region overridable).</li>
            <li>Region mismatch count (HLQ, DB2, RACF, JES, scheduler, volser, GDG retention).</li>
            <li>Backup-gap signal: protected resources without a paired UNLOAD/IMAGE COPY/REPRO.</li>
            <li>Historical ABEND priors for the program in the target region.</li>
          </ul>
        </CardContent>
      </Card>

      {/* BOB: hero-shot Confidence Score gauge per docs/CONFIDENCE_SCORE.md */}
      <BobStub
        feature="Confidence Score gauge"
        spec="Recharts radial gauge, 62/RED → 94 → 100/GREEN with smooth color transitions. Score breakdown panel below shows every component and its deduction. Plumbing: GET /api/score and POST /api/score."
      />
    </>
  );
}
