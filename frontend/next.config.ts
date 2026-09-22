import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Minimal, self-contained runtime for the Docker image — see
  // frontend/Dockerfile.
  output: "standalone",
};

export default nextConfig;
