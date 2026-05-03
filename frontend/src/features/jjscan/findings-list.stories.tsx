import type { Meta, StoryObj } from "@storybook/react";
import { FindingsList } from "./findings-list";
import type { Finding } from "@/lib/api/types";

const FOUR: Finding[] = [
  {
    id: "f1",
    rule_id: "JJ-COPYBOOK-DRIFT-001",
    severity: "high",
    description: "CBANKDAT resolves to v_VSAM in source / v_SQL in target.",
    details: { copybook: "CBANKDAT" },
    auto_fix_available: true,
    decision: "pending",
    created_at: "2026-05-03T00:00:00Z",
  },
  {
    id: "f2",
    rule_id: "JJ-MISSING-PROC-MEMBER-001",
    severity: "high",
    description: "PROC YBATTSO is referenced but not in target PROCLIB.",
    details: { proc: "YBATTSO" },
    auto_fix_available: false,
    decision: "pending",
    created_at: "2026-05-03T00:00:00Z",
  },
  {
    id: "f3",
    rule_id: "JJ-PROC-OVERRIDE-CONFLICT-001",
    severity: "medium",
    description: "DD STEPLIB on EXTRACT overridden with two distinct values.",
    details: { step: "EXTRACT", dd: "STEPLIB" },
    auto_fix_available: false,
    decision: "pending",
    created_at: "2026-05-03T00:00:00Z",
  },
  {
    id: "f4",
    rule_id: "JJ-DB2-PLAN-MISMATCH-001",
    severity: "critical",
    description: "DB2 subsystem DB10 referenced; target uses DB30.",
    details: { jcl_subsystem: "DB10", target_subsystem: "DB30" },
    auto_fix_available: true,
    decision: "pending",
    created_at: "2026-05-03T00:00:00Z",
  },
];

const meta: Meta<typeof FindingsList> = {
  title: "Features/JJSCAN+ Findings List",
  component: FindingsList,
};
export default meta;

type Story = StoryObj<typeof FindingsList>;

export const FourFindingsAcrossSeverities: Story = {
  args: { findings: FOUR },
};

export const WithDissentBanner: Story = {
  args: {
    findings: FOUR,
    dissent: {
      "JJ-COPYBOOK-DRIFT-001": {
        dismissedCount: 7,
        totalCount: 9,
        topReason: "Pinned by shop policy",
      },
    },
  },
};

export const Empty: Story = {
  args: { findings: [] },
};
