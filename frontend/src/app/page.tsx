// app/page.tsx
// ============
// 메인 홈페이지 컴포넌트
// - Text2SQL Agent 채팅 인터페이스
// - 백엔드 API 연동

'use client';

import React from 'react';
import ChatContainer from '@/components/chat/ChatContainer';

/**
 * 메인 페이지 컴포넌트
 * 
 * 주요 기능:
 * 1. ChatContainer를 통한 실시간 채팅
 * 2. 백엔드 API와 Socket.io 연동
 * 3. 공공데이터 분석 요청 처리
 */
export default function HomePage() {
  const handleMessageSend = (message: string) => {
    console.log('메시지 전송:', message);
  };

  const handleSessionChange = (sessionId: string) => {
    console.log('세션 변경:', sessionId);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* 메인 채팅 컨테이너 */}
      <ChatContainer
        onMessageSend={handleMessageSend}
        onSessionChange={handleSessionChange}
      />
    </div>
  );
} 