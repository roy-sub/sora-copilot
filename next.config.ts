import type { NextConfig } from "next";

// Static export (brief §8): no SSR, no server actions, no image optimisation.
const config: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default config;
