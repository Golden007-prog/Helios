// Node MSW server for vitest + Storybook test runs.
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
