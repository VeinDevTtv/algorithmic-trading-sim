import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    // Treat the web folder as the root to silence multi-lockfile warnings
    root: __dirname,
  },
};

export default nextConfig;
