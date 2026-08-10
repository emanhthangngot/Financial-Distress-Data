import { defineConfig, devices } from "@playwright/test";

/**
 * Assistant streaming evidence run (fixture mode, fake upstream).
 *
 * Boots a deterministic fake inference upstream and a fixture-mode app server
 * pointed at it, so streaming, timeout, refusal and malformed-response handling
 * are proved end to end without a live Supabase project or a real model.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_ASSISTANT_PORT ?? 3212);
const FAKE_PORT = Number(process.env.FAKE_UPSTREAM_PORT ?? 3322);
const baseURL = `http://127.0.0.1:${PORT}`;
const fakeURL = `http://127.0.0.1:${FAKE_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /assistant-streaming\.spec\.ts/,
  outputDir: "./e2e/.artifacts",
  retries: 0,
  reporter: [["list"]],
  use: { baseURL, screenshot: "off", trace: "retain-on-failure" },

  projects: [
    {
      name: "assistant-1440",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],

  webServer: [
    {
      command: `node e2e/fake-upstream.mjs`,
      url: `${fakeURL}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: { FAKE_UPSTREAM_PORT: String(FAKE_PORT) },
    },
    {
      command: `pnpm build && pnpm start --port ${PORT}`,
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      timeout: 240_000,
      env: {
        DISTRESSLENS_DATA_SOURCE: "fixture",
        DISTRESSLENS_FIXTURE_ROLE: "analyst",
        DISTRESSLENS_FIXTURE_AAL: "aal2",
        DISTRESSLENS_FIXTURE_PLANE: "on",
        DISTRESSLENS_INFERENCE_URL: `${fakeURL}/v1/chat/completions`,
        // The fake upstream never checks it; it must never reach a screenshot.
        DISTRESSLENS_INFERENCE_TOKEN: "fake-e2e-token",
        // Timeout branch must fire well before the hosting limit and keep the
        // suite fast: the fake "chậm" path sleeps 10s, so 2.5s wins here.
        ASSISTANT_TIMEOUT_MS: "2500",
        TZ: "Asia/Ho_Chi_Minh",
      },
    },
  ],
});
