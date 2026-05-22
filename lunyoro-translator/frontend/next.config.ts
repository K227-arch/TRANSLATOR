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

const nextConfig: NextConfig = {
  reactCompiler: true,
  turbopack: {},
  ...(isDocker && { output: "standalone" }),
};

export default withPWA(nextConfig);
