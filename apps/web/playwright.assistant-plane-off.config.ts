import { defineConfig, devices } from "@playwright/test";

/**
 * Plane-off assistant evidence run.
 *
 * A fixture-mode server with the evidence plane off. The route admits the
 * request (budget is fine), then answers with the `eks_off` stream before any
 * upstream call, so the panel shows what the analyst can still do instead.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_PLANEOFF_PORT ?? 3214);
const baseURL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /assistant-plane-off\.spec\.ts/,
  outputDir: "./e2e/.artifacts",
  retries: 0,
  reporter: [["list"]],
  use: { baseURL, screenshot: "off", trace: "retain-on-failure" },

  projects: [
    {
      name: "planeoff-1440",
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
      DISTRESSLENS_FIXTURE_PLANE: "off",
      TZ: "Asia/Ho_Chi_Minh",
    },
  },
});
