import type { Meta, StoryObj } from "@storybook/react";
import { RegionCard } from "./region-card";

const meta: Meta<typeof RegionCard> = {
  title: "Regions/RegionCard",
  component: RegionCard,
};
export default meta;

export const Production: StoryObj<typeof RegionCard> = {
  args: { region: { name: "prod", tier: "production", hlq: "PROD.PROD" } },
};

export const Sandbox: StoryObj<typeof RegionCard> = {
  args: { region: { name: "sandbox", tier: "sandbox", hlq: "PROD.SAND" } },
};
