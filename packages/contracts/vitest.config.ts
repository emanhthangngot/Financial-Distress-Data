import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    coverage: {
      enabled: true,
      provider: "v8",
      reporter: ["text", "html", "json-summary"],
      include: ["src/**/*.ts"],
      exclude: [
        "src/**/*.test.ts",
        // Build-time JSON data, not logic.
        "src/session-transitions.json",
        // A pure re-export barrel; every export it re-exports is covered by
        // that module's own test file, so importing this file would only
        // assert that `export *` works.
        "src/index.ts",
        "**/*.d.ts",
      ],
      thresholds: { lines: 90, branches: 90 },
    },
  },
});
