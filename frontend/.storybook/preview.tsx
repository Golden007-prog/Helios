import type { Preview } from "@storybook/react";
import "../src/app/globals.css";

const preview: Preview = {
  parameters: {
    backgrounds: { default: "dark" },
    controls: { expanded: true },
  },
  decorators: [
    (Story) => (
      <div data-theme="dark" className="bg-bg p-6 text-fg">
        <Story />
      </div>
    ),
  ],
};
export default preview;
