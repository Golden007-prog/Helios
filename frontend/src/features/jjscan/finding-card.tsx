"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Finding } from "@/lib/api/types";

const VARIANT = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "info",
} as const;

interface Props {
  finding: Finding;
  onAccept?: (f: Finding) => void;
  onDismiss?: (f: Finding) => void;
  onAutoFix?: (f: Finding) => void;
  dissentMessage?: string;
}

export function FindingCard({ finding, onAccept, onDismiss, onAutoFix, dissentMessage }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="font-mono text-sm">{finding.rule_id}</CardTitle>
          <Badge variant={VARIANT[finding.severity]}>{finding.severity}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm">{finding.description}</p>
        {dissentMessage && (
          <div className="mb-3 rounded-md border border-warning/40 bg-warning/5 p-2 text-xs text-warning">
            {dissentMessage}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {finding.auto_fix_available && onAutoFix && (
            <Button size="sm" onClick={() => onAutoFix(finding)}>
              Apply auto-fix
            </Button>
          )}
          {onAccept && (
            <Button size="sm" variant="secondary" onClick={() => onAccept(finding)}>
              Accept
            </Button>
          )}
          {onDismiss && (
            <Button size="sm" variant="ghost" onClick={() => onDismiss(finding)}>
              Dismiss
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
