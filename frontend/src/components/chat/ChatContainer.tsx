// components/chat/ChatContainer.tsx
// ==================================
// 메인 채팅 컨테이너 컴포넌트
// - 전체 채팅 UI의 최상위 컨테이너
// - 메시지 목록, 입력창, 상태 관리 통합
// - HTTP API 통신으로 백엔드 연동
// - 세션 관리 및 메시지 히스토리 처리

'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ChatContainerProps, Message } from '@/types';
import { useChatStore } from '@/hooks/useChatStore';
import { sendChatMessageStream, checkServerHealth } from '@/utils/api';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ChatHeader from './ChatHeader';

/**
 * ChatContainer 컴포넌트
 * 
 * 주요 기능:
 * 1. 실시간 채팅 메시지 표시 및 관리
 * 2. 사용자 입력 처리 및 백엔드 전송
 * 3. HTTP API를 통한 백엔드 통신
 * 4. 메시지 히스토리 및 세션 관리
 * 5. 로딩 상태, 오류 처리, 재시도 로직
 * 6. 자동 스크롤
 * 7. 메시지 복사, 재전송 기능
 */
const ChatContainer: React.FC<ChatContainerProps> = ({
  sessionId: propSessionId,
  initialMessages = [],
  onMessageSend,
  onSessionChange,
}) => {
  // ============================================================================
  // 상태 관리 (Zustand Store)
  // ============================================================================
  const {
    sessions,
    currentSessionId,
    addMessage,
    updateMessage,
    createSession,
    setCurrentSession,
    setConnectionStatus,
  } = useChatStore();

  // ============================================================================
  // 로컬 상태
  // ============================================================================
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [_currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('');
  const [_isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // ============================================================================
  // 현재 세션 및 메시지 계산
  // ============================================================================
  const activeSessionId = propSessionId || currentSessionId;
  const currentSession = sessions.find(s => s.id === activeSessionId);
  const messages = currentSession?.messages || initialMessages;

  // ============================================================================
  // 생명주기 및 이벤트 핸들러
  // ============================================================================

  /**
   * 컴포넌트 마운트 시 초기화
   * - 세션 생성 또는 기존 세션 연결
   * - 서버 상태 확인
   */
  useEffect(() => {
    let sessionId = activeSessionId;
    
    // 세션이 없으면 새로 생성
    if (!sessionId) {
      sessionId = createSession('새 채팅');
      setCurrentSession(sessionId);
      onSessionChange?.(sessionId);
    }

    // 서버 상태 확인
    checkServerHealth().then((healthy) => {
      setIsConnected(healthy);
      setConnectionStatus(healthy);
    });

    // 초기 환영 메시지 추가 (세션에 메시지가 없는 경우)
    if (sessionId && (!currentSession || currentSession.messages.length === 0)) {
      const welcomeMessage: Message = {
        id: `welcome-${Date.now()}`,
        content: '안녕하세요! Text2SQL Agent입니다. 공공데이터 분석에 대해 질문해보세요.',
        role: 'assistant',
        timestamp: new Date(),
      };
      addMessage(sessionId, welcomeMessage);
    }
  }, [activeSessionId, createSession, setCurrentSession, onSessionChange, setConnectionStatus, currentSession, addMessage]);

  /**
   * 메시지 변경 시 자동 스크롤
   */
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ============================================================================
  // 유틸리티 함수
  // ============================================================================

  /**
   * 메시지 목록 하단으로 스크롤
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /**
   * 스트리밍 메시지 전송 처리
   */
  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !activeSessionId) return;

    setIsLoading(true);
    setIsStreaming(true);
    setCurrentStreamingMessage('');

    // 사용자 메시지 즉시 추가
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content: content.trim(),
      role: 'user',
      timestamp: new Date(),
    };

    addMessage(activeSessionId, userMessage);

    // 스트리밍 응답을 위한 임시 메시지 ID
    const streamingMessageId = `streaming-${Date.now()}`;
    
    // 간단한 메시지 누적
    let currentContent = '';
    let isStreamingMessageAdded = false;

    try {
      // 스트리밍 API 호출
      await sendChatMessageStream({
        message: content.trim(),
        sessionId: activeSessionId,
        context: {
          previousMessages: messages.slice(-5), // 최근 5개 메시지만 컨텍스트로 전송
        },
      }, (update) => {
        console.log('스트리밍 업데이트:', update);

        // 완료된 단계만 추가 (중복 방지)
        if (update.type === 'start') {
          currentContent = `🚀 ${update.message}\n\n`;
        } else if (update.type === 'planning' && update.status === 'completed') {
          currentContent += `✅ 계획 수립 완료: ${update.data?.steps?.length || 0}개 단계\n`;
          if (update.data?.steps) {
            currentContent += update.data.steps.map((step: string, index: number) => 
              `${index + 1}. ${step}`
            ).join('\n') + '\n\n';
          }
        } else if (update.type === 'tool_call' && update.status === 'completed') {
          currentContent += `✅ 도구 실행 완료: ${update.tool_name || 'Unknown'}\n\n`;
        } else if (update.type === 'query' && update.status === 'completed') {
          currentContent += `✅ 쿼리 실행 완료\n\n`;
        } else if (update.type === 'visualization') {
          currentContent += `⚙️ **✅ 단계 ${update.step_number}: ${update.description}**\n\n`;
          if (update.chart_data) {
            currentContent += `📊 **차트가 생성되었습니다:**\n\n`;
          }
        } else if (update.type === 'result') {
          currentContent += `📈 **${update.message}**\n`;
        } else if (update.type === 'error') {
          currentContent += `❌ **오류 발생**\n${update.message}\n\n`;
        }

        // 첫 번째 업데이트에서만 메시지 추가, 이후는 업데이트만
        if (!isStreamingMessageAdded) {
          const streamingMessage: Message = {
            id: streamingMessageId,
            content: currentContent,
            role: 'assistant',
            timestamp: new Date(),
            metadata: {
              isStreaming: update.type !== 'done' && update.type !== 'result',
              chartData: update.chart_data || undefined,
              tableData: update.table_data || undefined
            }
          };
          addMessage(activeSessionId, streamingMessage);
          isStreamingMessageAdded = true;
        } else {
          // 기존 메시지 업데이트
          updateMessage(activeSessionId, streamingMessageId, {
            content: currentContent,
            metadata: {
              isStreaming: update.type !== 'done' && update.type !== 'result',
              chartData: update.chart_data || undefined,
              tableData: update.table_data || undefined
            }
          });
        }
      });

      setIsLoading(false);
      setIsStreaming(false);
      setCurrentStreamingMessage('');

      // 콜백 호출
      onMessageSend?.(content.trim());

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '메시지 전송에 실패했습니다.';
      setIsLoading(false);
      setIsStreaming(false);
      setCurrentStreamingMessage('');
      
      // 오류 메시지 추가
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        content: errorMessage,
        role: 'assistant',
        timestamp: new Date(),
        error: errorMessage,
      };
      addMessage(activeSessionId, errorMsg);
    }
  };

  /**
   * 메시지 재시도
   */
  const handleRetryMessage = async (messageId: string) => {
    const message = messages.find(m => m.id === messageId);
    if (!message || message.role !== 'user') return;

    await handleSendMessage(message.content);
  };

  /**
   * 메시지 복사
   */
  const handleCopyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      // TODO: 토스트 알림 표시
    } catch (err) {
      console.error('클립보드 복사 실패:', err);
    }
  };

  // ============================================================================
  // 렌더링
  // ============================================================================

  if (!activeSessionId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">채팅 세션을 초기화하는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="flex flex-col h-full bg-white dark:bg-gray-900"
    >
      {/* 채팅 헤더 */}
      <ChatHeader 
        session={currentSession || undefined}
        isConnected={isConnected}
        onClearHistory={() => {
          // TODO: 히스토리 삭제 구현
        }}
        onExportChat={() => {
          // TODO: 채팅 내보내기 구현
        }}
      />

      {/* 메시지 목록 */}
      <MessageList
        messages={messages}
        isLoading={isLoading}
        onRetry={handleRetryMessage}
        onCopy={handleCopyMessage}
        showTimestamps={true}
        groupByTime={true}
      />

      {/* 메시지 입력 */}
      <MessageInput
        onSend={handleSendMessage}
        disabled={isLoading || !isConnected}
        placeholder={
          !isConnected 
            ? "서버에 연결 중..." 
            : "메시지를 입력하세요... (예: 한국의 GDP 성장률을 분석해줘)"
        }
        maxLength={2000}
        suggestions={[
          "한국의 인구 통계를 보여주세요",
          "서울시 부동산 가격 동향을 분석해주세요",
          "최근 5년간 GDP 성장률을 비교해주세요"
        ]}
        isLoading={isLoading}
      />

      {/* 스크롤 참조점 */}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatContainer; 