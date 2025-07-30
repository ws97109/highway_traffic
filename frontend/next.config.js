/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    appDir: false, // 使用 pages 目錄結構
  },
  env: {
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY,
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
  images: {
    domains: ['maps.googleapis.com', 'maps.gstatic.com'],
  },
  webpack: (config, { isServer }) => {
    // 修復 leaflet 在 SSR 中的問題
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
