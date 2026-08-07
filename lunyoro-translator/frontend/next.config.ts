import type { NextConfig } from "next";
// eslint-disable-next-line @typescript-eslint/no-require-imports
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
    {
      urlPattern: /^https?.*/,
      handler: "NetworkFirst",
      options: {
        cacheName: "runyoro-api-cache",
        expiration: { maxEntries: 200, maxAgeSeconds: 7 * 24 * 60 * 60 },
        networkTimeoutSeconds: 10,
      },
    },
  ],
});

const isDocker = process.env.DOCKER_BUILD === "1";
// Static HTML/JS bundle for the Raspberry Pi, served by the C++ backend — no Node runtime.
const isStaticExport = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  reactCompiler: true,
  turbopack: {},
  // Allow Android emulator (10.0.2.2) and any local network device to access dev server
  allowedDevOrigins: ["10.0.2.2", "10.0.2.2:3002"],
  ...(isDocker && { output: "standalone" }),
  ...(isStaticExport && {
    output: "export",
    images: { unoptimized: true },
    trailingSlash: true,
  }),
};

export default withPWA(nextConfig);
