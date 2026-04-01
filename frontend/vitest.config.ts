import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  resolve: {
    tsconfigPaths: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    include: ["tests/**/*.test.{ts,tsx}", "features/**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next", "dist"],
    coverage: {
      provider: "istanbul",
      reporter: ["text", "lcov"],
      reportsDirectory: "./coverage",
      include: [
        "lib/**/*.ts",
        "lib/**/*.tsx",
        "features/*/hooks/*.ts",
        "features/*/services/*.ts",
      ],
      exclude: ["**/*.d.ts", "**/types/**"],
    },
    css: {
      modules: {
        classNameStrategy: "non-scoped",
      },
    },
  },
});
