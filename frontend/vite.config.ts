/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Vite is the frontend build/dev-server tool per ADR-0010 (React 18 +
// TypeScript is the SRS-fixed stack; Vite is the supporting build tool).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
    css: true,
  },
});
