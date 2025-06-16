// components/chat/TypingIndicator.tsx
// ===================================
// 타이핑 인디케이터 컴포넌트
// - AI가 응답을 생성 중일 때 표시
// - 애니메이션 효과로 시각적 피드백
// - 다양한 상태 메시지 표시

'use client';

import React from 'react';

interface TypingIndicatorProps {
  message?: string;
  showAvatar?: boolean;
}

/**
 * TypingIndicator 컴포넌트
 * 
 * 주요 기능:
 * 1. AI 응답 생성 중 시각적 피드백
 * 2. 애니메이션 점 3개로 타이핑 표현
 * 3. 커스텀 메시지 표시 가능
 * 4. 아바타 표시 옵션
 */
const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  message = "AI가 응답을 생성하고 있습니다...",
  showAvatar = true,
}) => {
  return (
    <div className="flex items-start space-x-3 px-4 py-2">
      {/* AI 아바타 */}
      {showAvatar && (
        <div className="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
          <svg
            className="w-4 h-4 text-blue-600 dark:text-blue-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
        </div>
      )}

      {/* 타이핑 버블 */}
      <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-3 max-w-xs">
        <div className="flex items-center space-x-2">
          {/* 애니메이션 점들 */}
          <div className="flex space-x-1">
            <div 
              className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
              style={{ animationDelay: '0ms' }}
            />
            <div 
              className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
              style={{ animationDelay: '150ms' }}
            />
            <div 
              className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
              style={{ animationDelay: '300ms' }}
            />
          </div>
          
          {/* 메시지 */}
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {message}
          </span>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator; 