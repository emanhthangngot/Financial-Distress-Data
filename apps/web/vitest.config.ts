import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // `server-only` throws on import outside a React Server Component, which
      // is exactly its job in the app and exactly wrong in a unit test. The
      // build still enforces the boundary; this only unblocks the test runner.
      "server-only": fileURLToPath(new URL("./src/test/server-only-stub.ts", import.meta.url)),
    },
  },
  test: {
    // Server-boundary and data-adapter units only. Route rendering and every
    // visual state are proved by the Playwright suite in e2e/, which runs the
    // real app rather than a simulated DOM.
    include: ["src/**/*.test.ts"],
    environment: "node",
  },
});
