// components/chat/ChatHeader.tsx
// ===============================
// 채팅 헤더 컴포넌트
// - 세션 제목, 연결 상태 표시
// - 채팅 설정, 내보내기, 삭제 등 액션
// - 실시간 연결 상태 인디케이터

'use client';

import React from 'react';
import { ChatSession } from '@/types';

interface ChatHeaderProps {
  session?: ChatSession | undefined;
  isConnected: boolean;
  onClearHistory?: () => void;
  onExportChat?: () => void;
  onSettings?: () => void;
}

/**
 * ChatHeader 컴포넌트
 * 
 * 주요 기능:
 * 1. 현재 채팅 세션 제목 표시
 * 2. 실시간 연결 상태 표시
 * 3. 채팅 액션 메뉴 (설정, 내보내기, 삭제)
 * 4. 세션 정보 (메시지 수, 생성 시간)
 */
const ChatHeader: React.FC<ChatHeaderProps> = ({
  session,
  isConnected,
  onClearHistory,
  onExportChat,
  onSettings,
}) => {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      {/* 왼쪽: 세션 정보 */}
      <div className="flex items-center space-x-3">
        {/* 연결 상태 인디케이터 */}
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`} />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {isConnected ? '연결됨' : '연결 끊김'}
          </span>
        </div>

        {/* 구분선 */}
        <div className="w-px h-4 bg-gray-300 dark:bg-gray-600" />

        {/* 세션 제목 */}
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            {session?.title || '새 채팅'}
          </h1>
          {session && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {session.messages.length}개 메시지 • {' '}
              {new Date(session.createdAt).toLocaleDateString('ko-KR')}
            </p>
          )}
        </div>
      </div>

      {/* 오른쪽: 액션 버튼들 */}
      <div className="flex items-center space-x-2">
        {/* 설정 버튼 */}
        {onSettings && (
          <button
            onClick={onSettings}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="설정"
          >
            <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        )}

        {/* 내보내기 버튼 */}
        {onExportChat && (
          <button
            onClick={onExportChat}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="채팅 내보내기"
          >
            <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
        )}

        {/* 히스토리 삭제 버튼 */}
        {onClearHistory && (
          <button
            onClick={onClearHistory}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="채팅 기록 삭제"
          >
            <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

export default ChatHeader; 