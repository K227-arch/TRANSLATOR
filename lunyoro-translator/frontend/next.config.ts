import type { NextConfig } from "next";
// eslint-disable-next-line @typescript-eslint/no-require-imports
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  // Enable in all environments — needed for offline support
  disable: false,
  runtimeCaching: [
    // ── Next.js static assets — cache first (they have content hashes) ──────
    {
      urlPattern: /\/_next\/static\/.*/,
      handler: "CacheFirst",
      options: {
        cacheName: "next-static",
        expiration: { maxEntries: 500, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    // ── Next.js image optimisation ──────────────────────────────────────────
    {
      urlPattern: /\/_next\/image\?.*/,
      handler: "CacheFirst",
      options: {
        cacheName: "next-images",
        expiration: { maxEntries: 100, maxAgeSeconds: 7 * 24 * 60 * 60 },
      },
    },
    // ── Translation API — StaleWhileRevalidate so offline still returns cached ──
    {
      urlPattern: /\/translate/,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "translation-api",
        expiration: { maxEntries: 500, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    // ── Dictionary / spellcheck API ─────────────────────────────────────────
    {
      urlPattern: /\/(dictionary|spellcheck|lookup)/,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "dictionary-api",
        expiration: { maxEntries: 1000, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    // ── All other network requests — NetworkFirst with offline fallback ──────
    {
      urlPattern: /^https?.*/,
      handler: "NetworkFirst",
      options: {
        cacheName: "runyoro-general",
        expiration: { maxEntries: 200, maxAgeSeconds: 7 * 24 * 60 * 60 },
        networkTimeoutSeconds: 5,
      },
    },
  ],
});

const isDocker = process.env.DOCKER_BUILD === "1";

const nextConfig: NextConfig = {
  reactCompiler: true,
  turbopack: {},
  // Allow Android emulator (10.0.2.2) and any local network device to access dev server
  allowedDevOrigins: ["10.0.2.2", "10.0.2.2:3002"],
  ...(isDocker && { output: "standalone" }),
};

export default withPWA(nextConfig);
