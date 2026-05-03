import type { Meta, StoryObj } from "@storybook/react";
import { ConfidenceGauge } from "./confidence-gauge";

const meta: Meta<typeof ConfidenceGauge> = {
  title: "Features/Confidence Gauge",
  component: ConfidenceGauge,
};
export default meta;

type Story = StoryObj<typeof ConfidenceGauge>;

export const MayaInitialRed: Story = {
  args: {
    score: 62,
    base: 100,
    deductions: [
      { key: "backup_gap", amount: 30, autoFixable: true },
      { key: "jjscan_high", amount: 10, autoFixable: true },
    ],
    boosts: [{ key: "soft_rounding", amount: 2 }],
    subjectName: "ZBNKDEL.jcl",
  },
};

export const MayaAfterBackupAmber: Story = {
  args: {
    score: 94,
    base: 100,
    deductions: [{ key: "jjscan_high", amount: 10, autoFixable: true }],
    boosts: [{ key: "soft_rounding", amount: 4 }],
    subjectName: "ZBNKDEL.jcl",
  },
};

export const ClearToPromoteGreen: Story = {
  args: {
    score: 100,
    base: 100,
    deductions: [],
    boosts: [],
    subjectName: "ZBNKDEL.jcl",
  },
};
