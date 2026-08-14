import { defineConfig, devices } from "@playwright/test";

/**
 * Live Supabase smoke run.
 *
 * Unlike the analyst/roles suites, this config boots the product against the
 * real Supabase project: `DISTRESSLENS_DATA_SOURCE` is deliberately NOT set, so
 * `resolveSession()` reads the live `profiles` table and real RLS. It is opt-in
 * (`pnpm e2e:live`) because it provisions one disposable operator and must
 * never run unattended in CI.
 *
 * The web server runs the production build with the Supabase env from
 * `.env.local`, which Next.js loads itself — this config only pins the port and
 * timezone.
 */

const PORT = Number(process.env.DISTRESSLENS_LIVE_E2E_PORT ?? 3212);
const baseURL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /(live-smoke|auth-lifecycle)\.spec\.ts/,
  outputDir: "./e2e/.artifacts",
  retries: 0,
  reporter: [["list"]],
  use: { baseURL, screenshot: "off", trace: "retain-on-failure" },

  projects: [
    {
      name: "live-1440",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],

  webServer: {
    command: `pnpm build && pnpm start --port ${PORT}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
    env: {
      // Deliberately no DISTRESSLENS_DATA_SOURCE: live Supabase session path.
      DISTRESSLENS_LIVE_E2E_PORT: String(PORT),
      TZ: "Asia/Ho_Chi_Minh",
    },
  },
});
