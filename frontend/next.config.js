// next.config.js
// --------------
// Next.js 프로젝트 환경설정/빌드/라우팅/플러그인 관리 파일
// - 공식 규칙/명세(.cursor/rules/rl-text2sql-public-api.md) 기반 설계/구현
// - 확장성/유지보수성/테스트 용이성 고려

/** @type {import('next').NextConfig} */
const nextConfig = {
  // 실험적 기능
  experimental: {
    // 향후 실험적 기능 추가 예정
  },

  // 서버 외부 패키지 (Next.js 15에서 이동됨)
  serverExternalPackages: ['socket.io-client'],

  // TypeScript 설정
  typescript: {
    // 빌드 시 타입 체크 무시 (CI/CD에서 별도 체크)
    ignoreBuildErrors: false,
  },

  // ESLint 설정
  eslint: {
    // 빌드 시 ESLint 무시 (CI/CD에서 별도 체크)
    ignoreDuringBuilds: false,
  },

  // 이미지 최적화
  images: {
    domains: [
      'localhost',
      // 향후 이미지 호스팅 도메인 추가
    ],
    formats: ['image/webp', 'image/avif'],
  },

  // 환경 변수
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY || 'default-value',
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_SOCKET_URL: process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:8000',
  },

  // 공개 런타임 설정
  publicRuntimeConfig: {
    // 클라이언트와 서버 모두에서 사용 가능
  },

  // 서버 전용 런타임 설정
  serverRuntimeConfig: {
    // 서버에서만 사용 가능
  },

  // 리다이렉트 설정
  async redirects() {
    return [
      // 예시: 구 경로에서 새 경로로 리다이렉트
      // {
      //   source: '/old-path',
      //   destination: '/new-path',
      //   permanent: true,
      // },
    ];
  },

  // 리라이트 설정 (프록시)
  async rewrites() {
    return [
      // API 프록시 설정
      {
        source: '/api/backend/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },

  // 헤더 설정
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // 보안 헤더
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
          // CORS 헤더 (개발 환경)
          ...(process.env.NODE_ENV === 'development' ? [
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
          ] : []),
        ],
      },
    ];
  },

  // 웹팩 설정 커스터마이징
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // 커스텀 웹팩 설정
    
    // 절대 경로 import 설정 (이미 tsconfig.json에서 설정되어 있지만 추가 보장)
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, 'src'),
    };

    // 개발 환경에서 소스맵 최적화
    if (dev) {
      config.devtool = 'eval-source-map';
    }

    // 번들 분석기 (환경 변수로 활성화)
    if (process.env.ANALYZE === 'true') {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'server',
          openAnalyzer: true,
        })
      );
    }

    return config;
  },

  // 출력 설정
  output: 'standalone', // Docker 배포를 위한 설정

  // 압축 설정
  compress: true,

  // 전원 설정
  poweredByHeader: false,

  // 트레일링 슬래시 설정
  trailingSlash: false,

  // 빌드 ID 생성
  generateBuildId: async () => {
    // 커스텀 빌드 ID (Git 커밋 해시 등)
    return process.env.BUILD_ID || 'development';
  },

  // 페이지 확장자
  pageExtensions: ['tsx', 'ts', 'jsx', 'js'],

  // 국제화 설정은 App Router에서 지원되지 않음 (제거)
  // 향후 App Router 국제화 방식으로 구현 예정

  // 성능 최적화 (swcMinify는 Next.js 15에서 기본값이므로 제거)
  
  // 컴파일러 설정
  compiler: {
    // styled-components 지원 (사용 시)
    styledComponents: false,
    // React 컴파일러 최적화
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error'],
    } : false,
  },
};

module.exports = nextConfig;

