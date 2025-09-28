import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    // Ensure Turbopack treats the web folder as the root
    // to silence multi-lockfile workspace root warnings
    rootDirectory: __dirname,
  },
};

export default nextConfig;
