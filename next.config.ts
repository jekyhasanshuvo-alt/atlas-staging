import type { NextConfig } from "next";
// A separate local build can be inspected without replacing a running checkout's build.
const config: NextConfig = {distDir: process.env.ATLAS_NEXT_DIST_DIR ?? ".next"};
export default config;
