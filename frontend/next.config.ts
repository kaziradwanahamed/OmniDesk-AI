import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cache Components / Partial Prefetching are opt-in optimizations that require
  // Suspense boundaries around URL-dependent client hooks (usePathname/useParams).
  // This app is fully dynamic and presentational, so they are disabled for now;
  // revisit once real data-fetching lands with proper streaming boundaries.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
