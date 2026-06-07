/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The app is fully client-rendered (all pages call the REST/SSE API from the browser), so it
  // exports to static files — deployable to any CDN / Render Static Site. NEXT_PUBLIC_API_BASE and
  // NEXT_PUBLIC_API_TOKEN are baked in at build time.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
