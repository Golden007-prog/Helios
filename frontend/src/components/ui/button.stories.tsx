import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./button";

const meta: Meta<typeof Button> = {
  title: "UI/Button",
  component: Button,
  args: { children: "Promote" },
};
export default meta;

export const Primary: StoryObj<typeof Button> = { args: { variant: "primary" } };
export const Secondary: StoryObj<typeof Button> = { args: { variant: "secondary" } };
export const Ghost: StoryObj<typeof Button> = { args: { variant: "ghost" } };
export const Danger: StoryObj<typeof Button> = { args: { variant: "danger" } };
