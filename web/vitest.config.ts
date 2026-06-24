import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["../tests/web/**/*.test.ts"],
    globals: false
  },
  resolve: {
    alias: {
      "@web": "/Users/andrey/Documents/projects/UrbanFlow-AI/web/src"
    }
  }
});