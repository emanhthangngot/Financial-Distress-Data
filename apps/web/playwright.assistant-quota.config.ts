import { defineConfig, devices } from "@playwright/test";

/**
 * Quota-exhausted assistant evidence run.
 *
 * A fixture-mode server whose budget env starts at zero, so the assistant's
 * first question is refused with the 429 reset copy. No fake upstream is
 * needed: the route refuses before the plane gate or proxy runs.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_QUOTA_PORT ?? 3213);
const baseURL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /assistant-quota\.spec\.ts/,
  outputDir: "./e2e/.artifacts",
  retries: 0,
  reporter: [["list"]],
  use: { baseURL, screenshot: "off", trace: "retain-on-failure" },

  projects: [
    {
      name: "quota-1440",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],

  webServer: {
    command: `pnpm build && pnpm start --port ${PORT}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
    env: {
      DISTRESSLENS_DATA_SOURCE: "fixture",
      DISTRESSLENS_FIXTURE_ROLE: "analyst",
      DISTRESSLENS_FIXTURE_AAL: "aal2",
      DISTRESSLENS_FIXTURE_PLANE: "on",
      DISTRESSLENS_FIXTURE_QUOTA_LEFT: "0",
      TZ: "Asia/Ho_Chi_Minh",
    },
  },
});
