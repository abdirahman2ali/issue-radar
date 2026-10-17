import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// A relative base makes the same build work at a domain root (custom domain) and under a
// subpath (github.io/issue-radar/). Set VITE_BASE to force an absolute base if ever needed.
export default defineConfig({
  base: process.env.VITE_BASE ?? "./",
  plugins: [react()],
  test: { environment: "node" },
});
