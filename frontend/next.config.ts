import type { NextConfig } from "next";

// Backend origin (without the /api/v1 suffix) for proxying stored media.
// Server-side rewrites run on the Next server, so use the in-network URL.
// NOTE: rewrites() is evaluated at build time and frozen into the build
// manifest, so in Docker this resolves to a placeholder (set in the
// Dockerfile) that entrypoint.sh swaps for the real API_URL_INTERNAL origin
// at container startup.
const backendOrigin = (
  process.env.API_URL_INTERNAL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8100/api/v1"
).replace(/\/api\/v1\/?$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // Model/source files (and images) are uploaded through server actions,
    // which default to a 1 MB body cap. Raise it above the backend's
    // MAX_UPLOAD_FILE_BYTES (100 MB) so large designs can be hosted here.
    serverActions: {
      bodySizeLimit: "110mb",
    },
  },
  // Stored media URLs are relative (/media/...). Proxy them to the backend
  // so they resolve against the frontend origin and work on any host.
  async rewrites() {
    return [
      {
        source: "/media/:path*",
        destination: `${backendOrigin}/media/:path*`,
      },
      // Tracking QR images, for the same reason. These are the only backend
      // assets the *browser* loads directly, so pointing them at
      // NEXT_PUBLIC_API_URL made them the one thing that breaks wherever the
      // API has no public origin — which is how it is deployed. Serving them
      // from this origin needs no public API and no build-time URL.
      {
        source: "/qr/:token",
        destination: `${backendOrigin}/api/v1/track/:token/qr.png`,
      },
    ];
  },
};

export default nextConfig;
