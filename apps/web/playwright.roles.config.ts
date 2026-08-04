import { defineConfig, devices } from "@playwright/test";

/**
 * Role and degraded-mode evidence run.
 *
 * The fixture identity is process-wide, so a role cannot change between tests
 * inside one server. This config therefore boots its own server as a platform
 * operator with the evidence plane off — the two conditions the analyst run
 * cannot cover — and runs only the specs that depend on them.
 *
 * Run it after the analyst suite: `pnpm e2e && pnpm e2e:roles`.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_ROLE_PORT ?? 3211);
const baseURL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /platform-surfaces\.spec\.ts/,
  outputDir: "./e2e/.artifacts",
  retries: 0,
  reporter: [["list"]],
  use: { baseURL, screenshot: "off", trace: "retain-on-failure" },

  projects: [
    {
      name: "operator-1440",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "operator-390",
      use: { ...devices["Pixel 5"], viewport: { width: 390, height: 844 } },
    },
  ],

  webServer: {
    command: `pnpm start --port ${PORT}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      DISTRESSLENS_DATA_SOURCE: "fixture",
      DISTRESSLENS_FIXTURE_ROLE: "platform_operator",
      DISTRESSLENS_FIXTURE_NAME: "Trần Quốc Vinh",
      DISTRESSLENS_FIXTURE_AAL: "aal2",
      // The condition the product must stay useful under.
      DISTRESSLENS_FIXTURE_PLANE: "off",
      TZ: "Asia/Ho_Chi_Minh",
    },
  },
});
