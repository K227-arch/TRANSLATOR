import type { NextConfig } from "next";

const isDocker = process.env.DOCKER_BUILD === "1";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // standalone output is only needed for Docker/self-hosted deployments
  // Vercel manages its own output format
  ...(isDocker && { output: "standalone" }),
};

export default nextConfig;
