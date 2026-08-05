import { defineConfig } from "@playwright/test";

/**
 * Accessibility run: platform operator identity, evidence plane off.
 *
 * Same route inventory as `playwright.a11y.config.ts` but under the identity
 * and degraded condition the analyst run cannot cover — a route this role is
 * denied still renders a forbidden state, and that state must be as
 * accessible as a success state.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_A11Y_ROLE_PORT ?? 3213);
const baseURL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /a11y\.spec\.ts/,
  outputDir: "./e2e/.artifacts",
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL,
    viewport: { width: 390, height: 844 },
  },

  webServer: {
    command: `pnpm build && pnpm start --port ${PORT}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: {
      DISTRESSLENS_DATA_SOURCE: "fixture",
      DISTRESSLENS_FIXTURE_ROLE: "platform_operator",
      DISTRESSLENS_FIXTURE_NAME: "Trần Quốc Vinh",
      DISTRESSLENS_FIXTURE_AAL: "aal2",
      DISTRESSLENS_FIXTURE_PLANE: "off",
      TZ: "Asia/Ho_Chi_Minh",
    },
  },
});
