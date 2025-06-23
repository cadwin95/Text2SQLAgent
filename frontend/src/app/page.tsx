// app/page.tsx
// ============
// 메인 홈페이지 컴포넌트
// - Text2SQL Agent 채팅 인터페이스
// - 백엔드 API 연동

'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * 메인 페이지 - IDE로 리디렉션
 * 
 * 통합된 SQL IDE 환경으로 바로 이동
 */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // IDE 페이지로 리디렉션
    router.push('/ide');
  }, [router]);

  // 로딩 화면 표시
  return (
    <div className="h-screen flex items-center justify-center bg-gray-900 text-white">
      <div className="text-center">
        <div className="text-6xl mb-4">🗃️</div>
        <h1 className="text-2xl font-bold mb-2">SQL IDE</h1>
        <p className="text-gray-400 mb-4">통합 데이터베이스 개발 환경으로 이동 중...</p>
        <div className="flex items-center justify-center space-x-1">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    </div>
  );
} 