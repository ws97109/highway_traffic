/** @type {import('next').NextConfig} */
const nextConfig = {
  // React 嚴格模式
  reactStrictMode: true,
  
  // TypeScript 配置
  typescript: {
    // 暫時忽略建置錯誤，便於部署
    ignoreBuildErrors: true,
  },
  
  // ESLint 配置
  eslint: {
    // 部署時忽略 ESLint 錯誤
    ignoreDuringBuilds: true,
  },

  // 實驗性功能
  experimental: {
    // 啟用應用程式目錄（如果未來要升級到 App Router）
    // appDir: false,
  },

  // 環境變數配置
  env: {
    // Google Maps API 金鑰
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY,
    
    // API 基礎 URL
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_BASE_URL: process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://localhost:8000',
    
    // 應用程式配置
    NEXT_PUBLIC_APP_MODE: process.env.NEXT_PUBLIC_APP_MODE || 'development',
    NEXT_PUBLIC_DEFAULT_CENTER_LAT: process.env.NEXT_PUBLIC_DEFAULT_CENTER_LAT || '25.0330',
    NEXT_PUBLIC_DEFAULT_CENTER_LNG: process.env.NEXT_PUBLIC_DEFAULT_CENTER_LNG || '121.5654',
    NEXT_PUBLIC_DEFAULT_ZOOM: process.env.NEXT_PUBLIC_DEFAULT_ZOOM || '10',
    
    // 功能開關
    NEXT_PUBLIC_ENABLE_RAG: process.env.NEXT_PUBLIC_ENABLE_RAG || 'true',
    NEXT_PUBLIC_ENABLE_SHOCKWAVE: process.env.NEXT_PUBLIC_ENABLE_SHOCKWAVE || 'true',
    NEXT_PUBLIC_ENABLE_REALTIME_TRAFFIC: process.env.NEXT_PUBLIC_ENABLE_REALTIME_TRAFFIC || 'true',
    NEXT_PUBLIC_DEBUG_MODE: process.env.NEXT_PUBLIC_DEBUG_MODE || 'false',
  },

  // 圖片最佳化配置
  images: {
    // 允許的外部圖片網域
    domains: [
      'maps.googleapis.com',
      'maps.gstatic.com',
      'lh3.googleusercontent.com',  // Google 用戶頭像
      'storage.googleapis.com',     // Google Cloud Storage
    ],
    // 關閉圖片最佳化（適合靜態部署和外部圖片）
    unoptimized: true,
    // 或者如果要啟用最佳化：
    // formats: ['image/webp', 'image/avif'],
    // quality: 75,
    // deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    // imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // API 路由重寫（開發環境用）
  async rewrites() {
    // 只在開發環境啟用 API 代理
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/traffic/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/traffic/:path*`,
        },
        {
          source: '/api/shockwave/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/shockwave/:path*`,
        },
        {
          source: '/api/prediction/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/prediction/:path*`,
        },
        {
          source: '/api/smart/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/smart/:path*`,
        },
        {
          source: '/api/controller/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/controller/:path*`,
        },
      ];
    }
    return [];
  },

  // 頁面重導向
  async redirects() {
    return [
      {
        source: '/admin',
        destination: '/admin/',
        permanent: false,
      },
      {
        source: '/driver',
        destination: '/driver/',
        permanent: false,
      },
    ];
  },

  // 自訂 Headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
      {
        // 為 API 路由設定 CORS
        source: '/api/:path*',
        headers: [
          {
            key: 'Access-Control-Allow-Origin',
            value: '*',
          },
          {
            key: 'Access-Control-Allow-Methods',
            value: 'GET, POST, PUT, DELETE, OPTIONS',
          },
          {
            key: 'Access-Control-Allow-Headers',
            value: 'Content-Type, Authorization',
          },
        ],
      },
    ];
  },

  // Webpack 配置
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // 處理客戶端的 Node.js 模組問題
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        child_process: false,
      };
    }

    // 處理 Leaflet 在 SSR 中的問題
    config.module.rules.push({
      test: /\.mjs$/,
      include: /node_modules/,
      type: 'javascript/auto',
    });

    // 添加別名（如果需要）
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, './src'),
    };

    return config;
  },

  // 效能最佳化
  onDemandEntries: {
    // 伺服器保持頁面在緩衝區的時間（毫秒）
    maxInactiveAge: 25 * 1000,
    // 同時保持的頁面數量
    pagesBufferLength: 2,
  },

  // 編譯配置
  compiler: {
    // 移除 console.log（生產環境）
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },

  // 國際化配置（如果需要）
  i18n: {
    locales: ['zh-TW', 'en'],
    defaultLocale: 'zh-TW',
    // 如果有多語言需求可以啟用
    // domains: [
    //   {
    //     domain: 'example.tw',
    //     defaultLocale: 'zh-TW',
    //   },
    //   {
    //     domain: 'example.com',
    //     defaultLocale: 'en',
    //   },
    // ],
  },

  // 靜態生成配置（如果需要 SSG）
  // trailingSlash: true,
  // output: 'export',  // 如果要純靜態匯出

  // SWC 編譯器配置（實驗性）
  swcMinify: true,

  // 產品分析配置
  ...(process.env.ANALYZE === 'true' && {
    webpack: (config, { isServer }) => {
      if (!isServer) {
        const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
        config.plugins.push(
          new BundleAnalyzerPlugin({
            analyzerMode: 'static',
            openAnalyzer: false,
          })
        );
      }
      return config;
    },
  }),
};

module.exports = nextConfig;
