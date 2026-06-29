import type { NextConfig } from "next";

// Backend origin (without the /api/v1 suffix) for proxying stored media.
// Server-side rewrites run on the Next server, so use the in-network URL.
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
    ];
  },
};

export default nextConfig;
