import type { NextConfig } from "next";

const isDocker = process.env.DOCKER_BUILD === "1";
// Static HTML/JS bundle for the Raspberry Pi, served by the C++ backend — no Node runtime.
const isStaticExport = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Allow Android emulator (10.0.2.2) and any local network device to access dev server
  allowedDevOrigins: ["10.0.2.2", "10.0.2.2:3002"],
  ...(isDocker && { output: "standalone" }),
  ...(isStaticExport && {
    output: "export",
    images: { unoptimized: true },
    trailingSlash: true,
  }),
};

export default nextConfig;
