import type { Meta, StoryObj } from "@storybook/react";
import { AnalysisPane } from "./analysis-pane";
import type { AbendAnalysisResponse } from "./types";

const CONFIRMED: AbendAnalysisResponse = {
  pattern_code: "S0C7",
  identified_abend: { code: "S0C7", confidence: 0.92, tier: "confirmed" },
  failing_step: { program: "CUSTPROC", step_name: "STEP010", offset_hex: "1A4" },
  source_trace: {
    paragraph: "2300-CALC-RETIREMENT",
    highlighted_field: "WS-DOB",
    line: 247,
  },
  business_rule_explanation:
    "S0C7 data exception: numeric op on non-numeric WS-DOB. Most likely cause is uninitialised field; READ from CUST.MASTER returned NULL.",
  ranked_root_causes: [
    { cause: "Uninitialised WS-DOB before MOVE", prior_count: 45, confidence: 0.92 },
    { cause: "Bad input record with non-numeric DOB", prior_count: 30, confidence: 0.78 },
    { cause: "DISPLAY value used where COMP-3 expected", prior_count: 18, confidence: 0.66 },
  ],
  matching_runbooks: [
    {
      id: "rb-cobol-s0c7-handling",
      title: "S0C7 Data Exception Troubleshooting",
      success_count: 127,
    },
  ],
  degraded: false,
  quarantine_sql: "DELETE FROM CUST WHERE DOB IS NULL;",
};

const UNFAMILIAR: AbendAnalysisResponse = {
  pattern_code: "Z99X",
  identified_abend: { code: "Z99X", confidence: 0.25, tier: "unfamiliar" },
  failing_step: {},
  source_trace: {},
  business_rule_explanation:
    "ABEND token Z99X found in the dump but no pattern in the library matched it confidently.",
  ranked_root_causes: [],
  matching_runbooks: [],
  degraded: true,
  degraded_reason: "unfamiliar_pattern",
};

const PROBABLE: AbendAnalysisResponse = {
  pattern_code: "U4038",
  identified_abend: { code: "U4038", confidence: 0.55, tier: "probable" },
  failing_step: { program: "CUSTPROC" },
  source_trace: {},
  business_rule_explanation:
    "U4038 LE user abend, often wraps an inner S0C7. Inspect the CEEDUMP for the inner exception.",
  ranked_root_causes: [
    { cause: "Inner S0C7 surfaced as U4038", prior_count: 22, confidence: 0.55 },
  ],
  matching_runbooks: [],
  degraded: false,
};

const meta: Meta<typeof AnalysisPane> = {
  title: "Features/ABEND/Analysis Pane",
  component: AnalysisPane,
};
export default meta;

type Story = StoryObj<typeof AnalysisPane>;

export const ConfirmedS0C7: Story = { args: { abend: CONFIRMED } };
export const ProbableU4038: Story = { args: { abend: PROBABLE } };
export const UnfamiliarZ99X: Story = { args: { abend: UNFAMILIAR } };
