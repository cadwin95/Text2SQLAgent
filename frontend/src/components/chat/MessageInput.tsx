// components/chat/MessageInput.tsx
// =================================
// 메시지 입력 컴포넌트
// - 텍스트 입력, 전송 버튼, 자동 완성
// - 키보드 단축키 (Enter, Shift+Enter)
// - 파일 업로드, 음성 입력 (향후)
// - 입력 제안, 명령어 자동완성

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { MessageInputProps } from '@/types';

/**
 * MessageInput 컴포넌트
 * 
 * 주요 기능:
 * 1. 텍스트 입력 및 전송
 * 2. 키보드 단축키 지원 (Enter, Shift+Enter)
 * 3. 자동 높이 조절 (멀티라인)
 * 4. 입력 제안 및 자동완성
 * 5. 로딩 상태 및 비활성화 처리
 * 6. 파일 업로드 (향후 구현)
 * 7. 음성 입력 (향후 구현)
 */
const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  disabled = false,
  placeholder = "메시지를 입력하세요...",
  maxLength = 2000,
  suggestions = [],
  isLoading = false,
}) => {
  // ============================================================================
  // 상태 관리
  // ============================================================================
  const [message, setMessage] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);
  const [isComposing, setIsComposing] = useState(false); // IME 입력 중 여부

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // ============================================================================
  // 이벤트 핸들러
  // ============================================================================

  /**
   * 메시지 전송 처리
   */
  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || disabled || isLoading) return;

    onSend(trimmedMessage);
    setMessage('');
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
    
    // 텍스트 영역 높이 초기화
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  /**
   * 키보드 이벤트 처리
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // IME 입력 중이면 무시
    if (isComposing) return;

    // 제안 목록이 열려있을 때 키보드 네비게이션
    if (showSuggestions && suggestions.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedSuggestionIndex(prev => 
            prev < suggestions.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedSuggestionIndex(prev => 
            prev > 0 ? prev - 1 : suggestions.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (selectedSuggestionIndex >= 0 && selectedSuggestionIndex < suggestions.length) {
            const selectedSuggestion = suggestions[selectedSuggestionIndex];
            if (selectedSuggestion) {
              handleSuggestionSelect(selectedSuggestion);
            }
          } else {
            handleSend();
          }
          break;
        case 'Escape':
          e.preventDefault();
          setShowSuggestions(false);
          setSelectedSuggestionIndex(-1);
          break;
      }
      return;
    }

    // 일반 키보드 단축키
    switch (e.key) {
      case 'Enter':
        if (e.shiftKey) {
          // Shift+Enter: 줄바꿈
          return;
        } else {
          // Enter: 전송
          e.preventDefault();
          handleSend();
        }
        break;
    }
  };

  /**
   * 텍스트 변경 처리
   */
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    
    // 최대 길이 제한
    if (value.length > maxLength) return;
    
    setMessage(value);
    
    // 자동 높이 조절
    adjustTextareaHeight();
    
    // 제안 표시 여부 결정
    const shouldShowSuggestions = value.length > 0 && suggestions.length > 0;
    setShowSuggestions(shouldShowSuggestions);
    
    if (!shouldShowSuggestions) {
      setSelectedSuggestionIndex(-1);
    }
  };

  /**
   * 제안 선택 처리
   */
  const handleSuggestionSelect = (suggestion: string) => {
    setMessage(suggestion);
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
    textareaRef.current?.focus();
  };

  /**
   * 텍스트 영역 높이 자동 조절
   */
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';
    const scrollHeight = textarea.scrollHeight;
    const maxHeight = 120; // 최대 높이 (약 6줄)
    
    textarea.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
  };

  // ============================================================================
  // 생명주기
  // ============================================================================

  useEffect(() => {
    adjustTextareaHeight();
  }, [message]);

  // ============================================================================
  // 렌더링
  // ============================================================================

  return (
    <div className="relative border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      {/* 제안 목록 */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute bottom-full left-0 right-0 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-t-lg shadow-lg max-h-40 overflow-y-auto"
        >
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => handleSuggestionSelect(suggestion)}
              className={`
                w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors
                ${index === selectedSuggestionIndex ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : ''}
                ${index === 0 ? 'rounded-t-lg' : ''}
                ${index === suggestions.length - 1 ? 'rounded-b-lg' : ''}
              `}
            >
              <div className="text-sm font-medium">{suggestion}</div>
            </button>
          ))}
        </div>
      )}

      {/* 입력 영역 */}
      <div className="flex items-end space-x-3 p-4">
        {/* 텍스트 입력 */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={`
              w-full resize-none rounded-lg border border-gray-300 dark:border-gray-600
              bg-white dark:bg-gray-800 text-gray-900 dark:text-white
              px-4 py-3 pr-12 focus:ring-2 focus:ring-blue-500 focus:border-transparent
              placeholder-gray-500 dark:placeholder-gray-400
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200
            `}
            style={{ minHeight: '48px' }}
          />
          
          {/* 글자 수 표시 */}
          {message.length > maxLength * 0.8 && (
            <div className={`
              absolute bottom-2 right-2 text-xs
              ${message.length >= maxLength ? 'text-red-500' : 'text-gray-400'}
            `}>
              {message.length}/{maxLength}
            </div>
          )}
        </div>

        {/* 전송 버튼 */}
        <button
          onClick={handleSend}
          disabled={disabled || isLoading || !message.trim()}
          className={`
            flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center
            transition-all duration-200 transform
            ${disabled || isLoading || !message.trim()
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white hover:scale-105 active:scale-95'
            }
          `}
          title={isLoading ? "전송 중..." : "메시지 전송 (Enter)"}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          )}
        </button>
      </div>

      {/* 도움말 텍스트 */}
      <div className="px-4 pb-2">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">Enter</kbd>로 전송, 
          <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs ml-1">Shift+Enter</kbd>로 줄바꿈
        </p>
      </div>
    </div>
  );
};

export default MessageInput; 