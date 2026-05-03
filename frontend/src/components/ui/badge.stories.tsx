import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./badge";

const meta: Meta<typeof Badge> = {
  title: "UI/Badge",
  component: Badge,
  args: { children: "critical" },
};
export default meta;

export const Critical: StoryObj<typeof Badge> = { args: { variant: "critical", children: "critical" } };
export const High: StoryObj<typeof Badge> = { args: { variant: "high", children: "high" } };
export const Medium: StoryObj<typeof Badge> = { args: { variant: "medium", children: "medium" } };
export const Low: StoryObj<typeof Badge> = { args: { variant: "low", children: "low" } };
