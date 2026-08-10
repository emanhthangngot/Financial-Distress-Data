import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // The contracts package ships TypeScript source rather than a build output,
  // so the app compiles it as part of its own graph. That keeps one definition
  // of the role/state/provenance rules instead of a published copy that can lag.
  transpilePackages: ["@distresslens/contracts"],
};

export default nextConfig;
