// ChatBox.tsx
// -----------
// 채팅 입력/출력 컴포넌트 파일
// - 사용자 자연어 질의 입력, LLM/백엔드 API와의 실시간 대화
// - 메시지 렌더링, 입력창/전송/로딩/오류/힌트 등 UX 확장
// - index.tsx(메인 페이지)에서 조합하여 사용
// - 공식 규칙/명세(.cursor/rules/rl-text2sql-public-api.md) 기반 설계/구현
// - 확장성/유지보수성/테스트 용이성 고려

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Message } from '@/types';

interface ChatBoxProps {
  onSendMessage?: (message: string) => void;
  messages?: Message[];
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * ChatBox 컴포넌트
 * 
 * 주요 기능:
 * - 사용자 자연어 질의 입력
 * - 메시지 히스토리 표시
 * - 실시간 채팅 인터페이스
 * - 로딩 상태 및 오류 처리
 */
const ChatBox: React.FC<ChatBoxProps> = ({
  onSendMessage,
  messages = [],
  isLoading = false,
  placeholder = "메시지를 입력하세요...",
  disabled = false,
}) => {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 메시지 목록 하단으로 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 입력창 높이 자동 조절
  const adjustTextareaHeight = () => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    adjustTextareaHeight();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || disabled || isLoading) return;

    onSendMessage?.(inputValue.trim());
    setInputValue('');
    
    // 높이 리셋
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
            <div className="text-lg mb-2">🤖 Text2SQL Agent</div>
            <p>공공데이터 분석에 대해 질문해보세요.</p>
            <div className="mt-4 text-sm">
              <p>예시:</p>
              <ul className="list-disc list-inside space-y-1 mt-2">
                <li>최근 5년간 GDP 성장률을 비교해주세요</li>
                <li>서울시 인구 변화를 차트로 보여주세요</li>
                <li>한국의 경제 지표를 분석해주세요</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] p-3 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                {message.timestamp && (
                  <div className="text-xs opacity-70 mt-1">
                    {new Date(message.timestamp).toLocaleTimeString('ko-KR')}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {/* 로딩 인디케이터 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-sm text-gray-600 dark:text-gray-400">분석 중...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled || isLoading}
              rows={1}
              className="w-full resize-none rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:cursor-not-allowed"
              style={{ minHeight: '40px', maxHeight: '120px' }}
            />
          </div>
          <button
            type="submit"
            disabled={!inputValue.trim() || disabled || isLoading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatBox;

