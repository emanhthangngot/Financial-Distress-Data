import { defineConfig } from "@playwright/test";

/**
 * Accessibility run: guest (signed-out) identity.
 *
 * Same route inventory as `playwright.a11y.config.ts`, but under the
 * identity `/sign-in`, `/sign-up`, and every other route's guest branch was
 * built for (RC1/RC2) -- a route a guest cannot use still renders a "sign
 * in" call to action, and that state must be as accessible as a success
 * state.
 */

const PORT = Number(process.env.DISTRESSLENS_E2E_A11Y_GUEST_PORT ?? 3214);
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
      DISTRESSLENS_FIXTURE_ROLE: "signed_out",
      DISTRESSLENS_FIXTURE_PLANE: "off",
      TZ: "Asia/Ho_Chi_Minh",
    },
  },
});
