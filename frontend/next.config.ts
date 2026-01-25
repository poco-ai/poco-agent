import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // NOTE: added for Docker deployment
  output: "standalone",
  // Disable image optimization for local development
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
