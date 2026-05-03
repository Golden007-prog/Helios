/** @type {import('next').NextConfig} */
const isPages = process.env.GITHUB_PAGES === "true";
const repoBase = process.env.PAGES_BASE_PATH ?? "/Helios";

const nextConfig = {
  output: "export",
  reactStrictMode: true,
  trailingSlash: true,
  images: { unoptimized: true },
  basePath: isPages ? repoBase : "",
  assetPrefix: isPages ? `${repoBase}/` : "",
  env: {
    NEXT_PUBLIC_BASE_PATH: isPages ? repoBase : "",
  },
};

export default nextConfig;
