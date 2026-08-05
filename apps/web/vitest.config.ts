import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const alias = {
  "@": fileURLToPath(new URL("./src", import.meta.url)),
  // `server-only` throws on import outside a React Server Component, which
  // is exactly its job in the app and exactly wrong in a unit test. The
  // build still enforces the boundary; this only unblocks the test runner.
  "server-only": fileURLToPath(new URL("./src/test/server-only-stub.ts", import.meta.url)),
};

export default defineConfig({
  resolve: { alias },
  test: {
    coverage: {
      enabled: true,
      provider: "v8",
      reporter: ["text", "html", "json-summary"],
      // Scoped to product logic (src/lib) and the four interactive surfaces
      // this stage's component tests were written for (assistant, the ops
      // action button, the disclaimer banner, the nav rail). The other
      // dozens of presentational components under src/components shipped in
      // an earlier phase with Playwright as their only proof and stay there
      // — gating the whole tree here would demand render tests for markup
      // that already has end-to-end coverage, which is padding, not a
      // meaningful check.
      include: [
        "src/lib/**/*.ts",
        "src/components/assistant/*.tsx",
        "src/components/ops/role-action-button.tsx",
        "src/components/shell/disclaimer-banner.tsx",
        "src/components/shell/nav-rail.tsx",
      ],
      exclude: [
        "src/lib/**/*.test.ts",
        "src/components/**/*.test.tsx",
        // Composition of already-tested lib code; Playwright asserts the
        // rendered result against the real app, not a simulated DOM.
        "src/app/**/page.tsx",
        "src/app/**/layout.tsx",
        // Data, not logic.
        "src/lib/data/fixtures/**",
        "src/lib/states/loading-copy.ts",
        // Client factories and a "use server" action: their real behavior is
        // a live Supabase/Next.js request context (headers, cookies, RPC),
        // which the RLS pytest suite and the Playwright role suites already
        // exercise. A unit test here would mostly assert mocks calling mocks.
        "src/lib/server/session.ts",
        "src/lib/server/session-actions.ts",
        "src/lib/server/supabase.ts",
        // Adapter-selection wiring exercised by the fixture-mode Playwright
        // run; port.ts is a pure type interface with no executable branches.
        "src/lib/data/index.ts",
        "src/lib/data/port.ts",
        "**/*.d.ts",
      ],
      thresholds: { lines: 90, branches: 90 },
    },
    projects: [
      {
        extends: true,
        test: {
          name: "lib",
          // Server-boundary and data-adapter units. Route rendering and every
          // visual state are proved by the Playwright suite in e2e/, which
          // runs the real app rather than a simulated DOM.
          include: ["src/**/*.test.ts"],
          environment: "node",
        },
      },
      {
        extends: true,
        test: {
          name: "components",
          // Interactive components whose behavior (state copy, role-gating,
          // focus) is otherwise only asserted end-to-end. Kept on a separate
          // jsdom project so a component test cannot accidentally rely on a
          // browser global the server code will not have.
          include: ["src/components/**/*.test.tsx"],
          environment: "jsdom",
          setupFiles: ["./src/test/setup-jsdom.ts"],
        },
      },
    ],
  },
});
