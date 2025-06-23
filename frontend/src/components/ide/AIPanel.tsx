'use client';

import React, { useState, useRef, useEffect } from 'react';
import { DatabaseConnection } from '@/types/database';

interface AIPanelProps {
  onAIQuery?: (question: string) => Promise<string | null>;
  currentConnection?: DatabaseConnection | null;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sqlQuery?: string;
}

export default function AIPanel({ onAIQuery, currentConnection }: AIPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const quickQuestions = [
    '이 데이터베이스의 테이블 목록을 보여주세요',
    '가장 큰 테이블은 무엇인가요?',
    '최근 7일간의 데이터를 조회해주세요',
    '사용자별 주문 건수를 집계해주세요',
    '매출 트렌드를 분석해주세요',
    '데이터 품질을 확인해주세요'
  ];

  const handleSendMessage = async (question?: string) => {
    const query = question || inputValue.trim();
    if (!query || isLoading) return;

    if (!currentConnection) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: '❌ 먼저 데이터베이스에 연결해주세요. 상단의 연결 관리 버튼을 클릭하여 데이터베이스에 연결하세요.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    // 사용자 메시지 추가
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      type: 'user',
      content: query,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const result = await onAIQuery?.(query);
      
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: result 
          ? `✅ SQL 쿼리가 생성되고 실행되었습니다.\n\n**생성된 쿼리:**\n\`\`\`sql\n${result}\n\`\`\``
          : '❌ 쿼리 생성에 실패했습니다. 다시 시도해주세요.',
        timestamp: new Date(),
        sqlQuery: result || undefined
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: `❌ 오류가 발생했습니다: ${error}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('ko-KR', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getConnectionStatusBadge = () => {
    if (!currentConnection) {
      return (
        <div className="flex items-center space-x-1 px-2 py-1 bg-red-900/30 border border-red-600 rounded text-xs">
          <div className="w-2 h-2 bg-red-400 rounded-full"></div>
          <span className="text-red-300">연결 없음</span>
        </div>
      );
    }

    return (
      <div className="flex items-center space-x-1 px-2 py-1 bg-green-900/30 border border-green-600 rounded text-xs">
        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
        <span className="text-green-300">{currentConnection.name}</span>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-gray-800">
      {/* Header */}
      <div className="p-3 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-white flex items-center">
            <span className="mr-2">🤖</span>
            AI Assistant
          </h3>
          <button
            onClick={() => setShowQuickActions(!showQuickActions)}
            className="text-xs text-gray-400 hover:text-white transition-colors"
            title="빠른 질문 토글"
          >
            {showQuickActions ? '🔽' : '🔼'}
          </button>
        </div>
        {getConnectionStatusBadge()}
      </div>

      {/* Quick Actions */}
      {showQuickActions && (
        <div className="p-3 border-b border-gray-700 bg-gray-850">
          <div className="text-xs text-gray-400 mb-2">빠른 질문:</div>
          <div className="grid grid-cols-1 gap-1">
            {quickQuestions.slice(0, 4).map((question, index) => (
              <button
                key={index}
                className="text-left text-xs text-blue-400 hover:text-blue-300 hover:bg-gray-700 p-2 rounded transition-colors"
                onClick={() => handleSendMessage(question)}
                disabled={isLoading || !currentConnection}
              >
                💡 {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 mt-8">
            <div className="text-4xl mb-2">💬</div>
            <p className="text-sm">
              {currentConnection 
                ? 'AI에게 데이터베이스에 대해 질문해보세요!' 
                : '먼저 데이터베이스에 연결하세요'
              }
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] p-3 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-100'
                }`}
              >
                <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                <div className={`text-xs mt-1 ${
                  message.type === 'user' ? 'text-blue-200' : 'text-gray-400'
                }`}>
                  {formatTimestamp(message.timestamp)}
                </div>
              </div>
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-700 text-gray-100 p-3 rounded-lg">
              <div className="text-sm">AI가 쿼리를 생성하고 있습니다...</div>
              <div className="flex space-x-1 mt-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-gray-700">
        <div className="flex space-x-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              currentConnection 
                ? "AI에게 질문하세요... (예: '사용자 테이블의 구조를 보여주세요')"
                : "먼저 데이터베이스에 연결하세요"
            }
            className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
            disabled={isLoading || !currentConnection}
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={isLoading || !inputValue.trim() || !currentConnection}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-md transition-colors self-end"
          >
            {isLoading ? '⏳' : '📤'}
          </button>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-2 mt-3">
          <button
            onClick={() => handleSendMessage('테이블 목록을 보여주세요')}
            disabled={isLoading || !currentConnection}
            className="px-3 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 text-white rounded text-xs transition-colors"
          >
            📋 테이블 목록
          </button>
          <button
            onClick={() => handleSendMessage('데이터베이스 스키마를 분석해주세요')}
            disabled={isLoading || !currentConnection}
            className="px-3 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 text-white rounded text-xs transition-colors"
          >
            🔍 스키마 분석
          </button>
        </div>
      </div>
    </div>
  );
} 