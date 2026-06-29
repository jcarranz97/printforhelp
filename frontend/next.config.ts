import type { NextConfig } from "next";

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
};

export default nextConfig;
