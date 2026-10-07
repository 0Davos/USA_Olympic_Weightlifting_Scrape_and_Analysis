import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Local dev only: proxy /api/* to the FastAPI server (run it with uvicorn on port 8000).
    // In production the Python functions are served under /api by the host, so nothing to proxy.
    if (process.env.NODE_ENV !== "development") return [];
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
  },
};

export default nextConfig;
