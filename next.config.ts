import type { NextConfig } from "next";
// A separate local build can be inspected without replacing a running checkout's build.
const staging = process.env.NEXT_PUBLIC_ATLAS_STAGING_DEMO === "true";
const config: NextConfig = {
  distDir: process.env.ATLAS_NEXT_DIST_DIR ?? ".next",
  ...(staging ? { turbopack: { resolveAlias: { "@/data/mock": "./src/data/staging-demo.ts" } } } : {}),
};
export default config;
