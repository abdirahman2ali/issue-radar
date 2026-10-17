import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// GitHub Pages serves a project site from /<repo>/, so the deploy sets VITE_BASE=/issue-radar/.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  test: { environment: "node" },
});
