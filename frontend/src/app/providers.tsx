// app/providers.tsx
// =================
// 전역 프로바이더 컴포넌트
// - React Query, 테마, 토스트 등 프로바이더 통합
// - 클라이언트 사이드 전용 컴포넌트

'use client';

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'react-hot-toast';

// React Query 클라이언트 설정
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5분
      cacheTime: 1000 * 60 * 30, // 30분 (v4에서는 cacheTime 사용)
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

/**
 * 전역 프로바이더 컴포넌트
 * 
 * 주요 기능:
 * 1. React Query 프로바이더 설정
 * 2. 토스트 알림 프로바이더
 * 3. 개발 도구 (React Query Devtools)
 * 4. 향후 테마, 인증 프로바이더 추가 예정
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {/* 토스트 알림 */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      
      {/* 메인 앱 */}
      {children}
      
      {/* 개발 도구 (개발 환경에서만) */}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
} 