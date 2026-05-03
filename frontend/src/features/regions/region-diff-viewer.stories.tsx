import type { Meta, StoryObj } from "@storybook/react";
import { RegionDiffViewer } from "./region-diff-viewer";

const meta: Meta<typeof RegionDiffViewer> = {
  title: "Features/Region Diff Viewer",
  component: RegionDiffViewer,
};
export default meta;

type Story = StoryObj<typeof RegionDiffViewer>;

export const SevenSubstitutionFields: Story = {
  args: {
    regionA: "int2",
    regionB: "int3",
    fields: [
      { path: "tier", a: "integration", b: "integration", kind: "value_change" },
      { path: "hlq", a: "CUST.INT2", b: "CUST.INT3", kind: "value_change" },
      {
        path: "db2.subsystem_id",
        a: "DBI2",
        b: "DBI3",
        kind: "value_change",
      },
      {
        path: "db2.plan_collection",
        a: "CUSTPKG.INT2",
        b: "CUSTPKG.INT3",
        kind: "value_change",
      },
      { path: "racf_group", a: "INT2DEV", b: "INT3DEV", kind: "value_change" },
      { path: "jes.class_", a: "A", b: "P", kind: "value_change" },
      { path: "scheduler_queue", a: "BATCH_DEV", b: "BATCH_INT", kind: "value_change" },
    ],
  },
};

export const AllAlignedEmptyState: Story = {
  args: {
    regionA: "int2",
    regionB: "int2",
    fields: [],
  },
};

export const MixedKinds: Story = {
  args: {
    regionA: "dev1",
    regionB: "prod",
    fields: [
      { path: "hlq", a: "CUST.DEV1", b: "CUST.PROD", kind: "value_change" },
      { path: "protected_resources[0]", a: null, b: "CUST.MASTER", kind: "added" },
      { path: "scheduler_queue", a: "BATCH_DEV", b: null, kind: "removed" },
    ],
  },
};
