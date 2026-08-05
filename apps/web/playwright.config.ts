import { defineConfig, devices } from "@playwright/test";

/**
 * Evidence run configuration.
 *
 * Three viewports, because the phase-02 contract names 1440, 1024 and 390 and a
 * layout that only works at one of them has not been proved. Role and plane
 * state are supplied per project through the fixture session's environment
 * variables, so one suite can exercise every role without a live Supabase
 * project.
 *
 * Screenshots are the deliverable here, not a side effect: `--update-snapshots`
 * regenerates them, and the manifest written by `evidence-manifest.ts` records
 * what each one actually shows.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_PORT ?? 3210);
const baseURL = `http://127.0.0.1:${PORT}`;

/** Fixture identity shared by every project; roles are overridden per project. */
const fixtureEnv = {
  DISTRESSLENS_DATA_SOURCE: "fixture",
  DISTRESSLENS_FIXTURE_AAL: "aal2",
  // Fixed timezone so timestamps in screenshots are byte-stable across machines.
  TZ: "Asia/Ho_Chi_Minh",
};

export default defineConfig({
  testDir: "./e2e",
  // The platform suite needs an operator identity and a plane-off server, the
  // assistant suites need their own fake upstream / quota / plane env, and the
  // live smoke run needs a real Supabase project. Each runs under its own
  // config; the default run covers the analyst evidence only.
  testIgnore: [
    /platform-surfaces\.spec\.ts/,
    /live-smoke\.spec\.ts/,
    /assistant-streaming\.spec\.ts/,
    /assistant-quota\.spec\.ts/,
    /assistant-plane-off\.spec\.ts/,
  ],
  outputDir: "./e2e/.artifacts",
  // Evidence must be reproducible, so a flaky pass is a failure.
  retries: 0,
  fullyParallel: true,
  reporter: [["list"], ["json", { outputFile: "e2e/.artifacts/results.json" }]],

  use: {
    baseURL,
    // The reference PNGs are the immutable baseline; run screenshots are new
    // artifacts recorded beside them rather than overwriting them.
    screenshot: "off",
    trace: "retain-on-failure",
  },

  projects: [
    {
      name: "desktop-1440",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "tablet-1024",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1024, height: 768 } },
    },
    {
      // Chromium-based mobile emulation rather than the iPhone descriptor: the
      // iPhone presets run WebKit, and the evidence run must not depend on a
      // second browser engine being installed to produce a 390px frame.
      name: "mobile-390",
      use: {
        ...devices["Pixel 5"],
        viewport: { width: 390, height: 844 },
      },
    },
  ],

  webServer: {
    command: `pnpm build && pnpm start --port ${PORT}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: {
      ...fixtureEnv,
      // The default project identity; per-test role changes go through the
      // dedicated role servers in the role suite.
      DISTRESSLENS_FIXTURE_ROLE: process.env.DISTRESSLENS_FIXTURE_ROLE ?? "analyst",
      DISTRESSLENS_FIXTURE_PLANE: process.env.DISTRESSLENS_FIXTURE_PLANE ?? "on",
    },
  },
});
