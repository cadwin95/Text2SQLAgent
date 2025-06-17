// app/layout.tsx
// ==============
// Next.js 14 App Router 루트 레이아웃
// - 전역 스타일, 메타데이터, 프로바이더 설정
// - 다크모드, 폰트, SEO 최적화
// - React Query, Zustand 프로바이더 래핑

import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AI Assistant - 통합 대화형 AI',
  description: '일반 대화와 데이터 분석을 모두 지원하는 차세대 AI 어시스턴트',
  keywords: ['AI Assistant', '대화형 AI', 'ChatGPT', '데이터 분석', 'KOSIS', '통계청', 'MCP'],
  authors: [{ name: 'AI Assistant Team' }],
  robots: 'index, follow',
  openGraph: {
    title: 'AI Assistant - 통합 대화형 AI',
    description: '일반 대화와 데이터 분석을 모두 지원하는 차세대 AI 어시스턴트',
    type: 'website',
    locale: 'ko_KR',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AI Assistant',
    description: '일반 대화와 데이터 분석을 모두 지원하는 차세대 AI 어시스턴트',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

/**
 * 루트 레이아웃 컴포넌트
 * 
 * 주요 기능:
 * 1. 전역 스타일 및 폰트 적용
 * 2. 메타데이터 및 SEO 설정
 * 3. 프로바이더 래핑 (React Query, Zustand, Theme)
 * 4. 다크모드 지원
 * 5. 반응형 레이아웃
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        {/* 추가 메타 태그 */}
        <meta name="theme-color" content="#3b82f6" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="format-detection" content="telephone=no" />
        
        {/* 파비콘 */}
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        
        {/* 프리로드 */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className={`${inter.className} antialiased`}>
        {/* 프로바이더로 앱 래핑 */}
        <Providers>
          {/* 메인 앱 컨테이너 */}
          <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
            {children}
          </div>
        </Providers>
        
        {/* 개발 환경에서만 표시되는 디버그 정보 */}
        {process.env.NODE_ENV === 'development' && (
          <div className="fixed bottom-4 right-4 z-50">
            <div className="bg-black/80 text-white text-xs px-2 py-1 rounded">
              <div>환경: {process.env.NODE_ENV}</div>
              <div>화면: <span className="sm:hidden">mobile</span><span className="hidden sm:inline md:hidden">tablet</span><span className="hidden md:inline">desktop</span></div>
            </div>
          </div>
        )}
      </body>
    </html>
  );
} 