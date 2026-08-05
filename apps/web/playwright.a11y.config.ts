import { defineConfig } from "@playwright/test";

/**
 * Accessibility run: analyst identity, evidence plane on.
 *
 * A self-contained Playwright project so `pnpm --filter @distresslens/web
 * e2e:a11y` is a reviewable command on its own, rather than an assertion
 * buried inside the evidence run.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_A11Y_PORT ?? 3212);
const baseURL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /a11y\.spec\.ts/,
  outputDir: "./e2e/.artifacts",
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL,
    viewport: { width: 1440, height: 900 },
  },

  webServer: {
    command: `pnpm build && pnpm start --port ${PORT}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: {
      DISTRESSLENS_DATA_SOURCE: "fixture",
      DISTRESSLENS_FIXTURE_ROLE: "analyst",
      DISTRESSLENS_FIXTURE_AAL: "aal2",
      DISTRESSLENS_FIXTURE_PLANE: "on",
      TZ: "Asia/Ho_Chi_Minh",
    },
  },
});
