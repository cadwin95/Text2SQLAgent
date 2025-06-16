// components/chat/MessageList.tsx
// ================================
// 채팅 메시지 목록 컴포넌트
// - 메시지들을 스크롤 가능한 목록으로 표시
// - 사용자/AI 메시지 구분하여 렌더링
// - 가상화(virtualization)로 성능 최적화
// - 메시지 그룹핑, 시간 표시, 상태 표시

'use client';

import React, { useMemo } from 'react';
import { Message } from '@/types';
import MessageBubble from './MessageBubble';

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
  onRetry?: (messageId: string) => void;
  onCopy?: (content: string) => void;
  showTimestamps?: boolean;
  groupByTime?: boolean;
}

/**
 * MessageList 컴포넌트
 * 
 * 주요 기능:
 * 1. 메시지 목록을 시간순으로 표시
 * 2. 사용자/AI 메시지 구분 렌더링
 * 3. 메시지 그룹핑 (같은 발신자, 연속 메시지)
 * 4. 시간 구분선 표시 (날짜 변경 시)
 * 5. 로딩 상태 및 오류 메시지 처리
 * 6. 메시지 액션 (복사, 재시도, 삭제)
 * 7. 가상화를 통한 대량 메시지 성능 최적화
 */
const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading = false,
  onRetry,
  onCopy,
  showTimestamps = true,
  groupByTime = true,
}) => {
  // ============================================================================
  // 메시지 그룹핑 및 처리
  // ============================================================================

  /**
   * 메시지를 그룹핑하여 렌더링 최적화
   * - 같은 발신자의 연속 메시지 그룹핑
   * - 시간 간격에 따른 구분
   * - 날짜 변경 시 구분선 추가
   */
  const processedMessages = useMemo(() => {
    if (!messages.length) return [];

    const processed = [];
    let currentGroup: Message[] = [];
    let lastSender: string | null = null;
    let lastDate: string | null = null;

    for (let i = 0; i < messages.length; i++) {
      const message = messages[i];
      if (!message) continue;
      
      const messageDate = new Date(message.timestamp).toDateString();
      const prevMessage = i > 0 ? messages[i - 1] : null;
      const timeDiff = prevMessage
        ? new Date(message.timestamp).getTime() - new Date(prevMessage.timestamp).getTime()
        : 0;

      // 날짜가 바뀌면 날짜 구분선 추가
      if (groupByTime && lastDate && lastDate !== messageDate) {
        if (currentGroup.length > 0) {
          processed.push({
            type: 'group',
            messages: [...currentGroup],
            sender: lastSender,
          });
          currentGroup = [];
        }
        
        processed.push({
          type: 'date-separator',
          date: messageDate,
        });
      }

      // 발신자가 바뀌거나 시간 간격이 5분 이상이면 새 그룹 시작
      const shouldStartNewGroup = 
        message.role !== lastSender || 
        timeDiff > 5 * 60 * 1000; // 5분

      if (shouldStartNewGroup && currentGroup.length > 0) {
        processed.push({
          type: 'group',
          messages: [...currentGroup],
          sender: lastSender,
        });
        currentGroup = [];
      }

      currentGroup.push(message);
      lastSender = message.role;
      lastDate = messageDate;
    }

    // 마지막 그룹 추가
    if (currentGroup.length > 0) {
      processed.push({
        type: 'group',
        messages: currentGroup,
        sender: lastSender,
      });
    }

    return processed;
  }, [messages, groupByTime]);

  // ============================================================================
  // 렌더링 헬퍼
  // ============================================================================

  /**
   * 날짜 구분선 렌더링
   */
  const renderDateSeparator = (date: string) => {
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toDateString();
    
    let displayDate = date;
    if (date === today) {
      displayDate = '오늘';
    } else if (date === yesterday) {
      displayDate = '어제';
    } else {
      displayDate = new Date(date).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    }

    return (
      <div className="flex items-center justify-center my-4">
        <div className="flex-1 border-t border-gray-200 dark:border-gray-700"></div>
        <div className="px-4 py-1 bg-gray-100 dark:bg-gray-800 rounded-full">
          <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
            {displayDate}
          </span>
        </div>
        <div className="flex-1 border-t border-gray-200 dark:border-gray-700"></div>
      </div>
    );
  };

  /**
   * 메시지 그룹 렌더링
   */
  const renderMessageGroup = (group: any, index: number) => {
    const { messages: groupMessages, sender } = group;
    const isUser = sender === 'user';
    const isSystem = sender === 'system';

    return (
      <div
        key={`group-${index}`}
        className={`flex flex-col space-y-1 mb-4 ${
          isUser ? 'items-end' : 'items-start'
        }`}
      >
        {/* 발신자 표시 (시스템 메시지가 아닌 경우) */}
        {!isSystem && showTimestamps && (
          <div className={`text-xs text-gray-500 dark:text-gray-400 mb-1 ${
            isUser ? 'text-right' : 'text-left'
          }`}>
            {isUser ? '나' : 'AI 어시스턴트'}
            <span className="ml-2">
              {new Date(groupMessages[0].timestamp).toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        )}

        {/* 메시지들 */}
        {groupMessages.map((message: Message, msgIndex: number) => (
          <MessageBubble
            key={message.id}
            message={message}
            isLast={msgIndex === groupMessages.length - 1}
            showTimestamp={false} // 그룹 단위로 시간 표시
            onRetry={onRetry}
            onCopy={onCopy}
          />
        ))}
      </div>
    );
  };

  // ============================================================================
  // 메인 렌더링
  // ============================================================================

  if (!messages.length && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-400 dark:text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            새로운 채팅을 시작하세요
          </h3>
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            공공데이터 분석이나 질문을 입력해보세요.
            <br />
            AI가 데이터를 찾아서 분석해드립니다.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-2">
      {/* 처리된 메시지 그룹들 렌더링 */}
      {processedMessages.map((item, index) => {
        if (item.type === 'date-separator' && item.date) {
          return renderDateSeparator(item.date);
        }
        
        if (item.type === 'group') {
          return renderMessageGroup(item, index);
        }
        
        return null;
      })}

      {/* 로딩 인디케이터 */}
      {isLoading && (
        <div className="flex items-start space-x-3 mb-4">
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
          <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-3">
            <div className="flex items-center space-x-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                AI가 응답을 생성하고 있습니다...
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList; 