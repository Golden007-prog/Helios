import type { Meta, StoryObj } from "@storybook/react";
import { QueueCard } from "./queue-card";

const meta: Meta<typeof QueueCard> = {
  title: "Features/Queue/Card",
  component: QueueCard,
};
export default meta;

type Story = StoryObj<typeof QueueCard>;

export const PendingPromote: Story = {
  args: {
    item: {
      event_id: "evt:01",
      state: "pending_review",
      type: "promote",
      initiator: "maya@meridianbank.demo",
      reviewers: ["anil@meridianbank.demo"],
      created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      payload: {
        jcl: "ZBNKDEL.jcl",
        score: 62,
        top_reasons: [
          "Backup gap (-30)",
          "Copybook drift (-10)",
          "JES class T → P (-3)",
        ],
      },
    },
    currentUserEmail: "anil@meridianbank.demo",
    onApprove: () => {},
    onReject: () => {},
    onViewDiff: () => {},
  },
};

export const SelfReview: Story = {
  args: {
    item: {
      ...PendingPromote.args!.item!,
      event_id: "evt:02",
    },
    currentUserEmail: "maya@meridianbank.demo",
  },
};

export const HighScoreApproved: Story = {
  args: {
    item: {
      event_id: "evt:03",
      state: "auto_approved",
      type: "promote",
      initiator: "maya@meridianbank.demo",
      reviewers: [],
      created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      payload: {
        jcl: "ZBNKINT1.jcl",
        score: 96,
        top_reasons: ["Spec match bonus (+10)"],
      },
    },
    currentUserEmail: "anil@meridianbank.demo",
  },
};
