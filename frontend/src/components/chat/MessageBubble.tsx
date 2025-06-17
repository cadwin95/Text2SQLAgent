// components/chat/MessageBubble.tsx
// ==================================
// 개별 메시지 버블 컴포넌트
// - 사용자/AI 메시지를 구분하여 스타일링
// - 메시지 내용, 시간, 상태 표시
// - 액션 버튼 (복사, 재시도, 삭제)
// - 마크다운 렌더링, 코드 하이라이팅

'use client';

import React, { useState } from 'react';
import { MessageBubbleProps } from '@/types';
import ChartDisplay from '../chart/ChartDisplay';
import QueryResultTable from '../QueryResultTable';
import QueryResultChart from '../QueryResultChart';

/**
 * MessageBubble 컴포넌트
 * 
 * 주요 기능:
 * 1. 사용자/AI 메시지 구분 스타일링
 * 2. 메시지 내용 렌더링 (텍스트, 마크다운, 코드)
 * 3. 시간 표시 및 상태 표시 (전송중, 오류 등)
 * 4. 액션 메뉴 (복사, 재시도, 삭제)
 * 5. 데이터 테이블/차트 렌더링
 * 6. 호버 효과 및 애니메이션
 */
const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isLast = false,
  showTimestamp = true,
  onRetry,
  onCopy,
}) => {
  const [showActions, setShowActions] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  // ============================================================================
  // 스타일 계산
  // ============================================================================

  const bubbleClasses = `
    relative max-w-[80%] px-4 py-3 rounded-lg break-words
    ${isUser 
      ? 'bg-blue-600 text-white ml-auto' 
      : isSystem
        ? 'bg-yellow-100 text-yellow-800 border border-yellow-200 mx-auto'
        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
    }
    ${message.isLoading ? 'opacity-70' : ''}
    ${message.error ? 'border-2 border-red-300 bg-red-50' : ''}
    transition-all duration-200 ease-in-out
    ${isHovered ? 'shadow-md' : 'shadow-sm'}
  `.trim();

  // ============================================================================
  // 이벤트 핸들러
  // ============================================================================

  const handleCopy = () => {
    onCopy?.(message.content);
  };

  const handleRetry = () => {
    if (message.role === 'user') {
      onRetry?.(message.id);
    }
  };

  // ============================================================================
  // 렌더링 헬퍼
  // ============================================================================

  /**
   * 데이터 테이블 렌더링
   */
  // @ts-ignore - TODO: 향후 사용 예정
  const renderDataTable = (tableData: any) => {
    if (!tableData || !tableData.columns || !tableData.rows) return null;

    const { columns, rows, total_rows, query_code } = tableData;
    
    return (
      <div className="mt-4 border rounded-lg overflow-hidden bg-white dark:bg-gray-800">
        {/* 쿼리 코드 표시 */}
        {query_code && (
          <div className="bg-gray-50 dark:bg-gray-700 px-3 py-2 border-b">
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">실행된 쿼리:</div>
            <code className="text-sm font-mono text-blue-600 dark:text-blue-400">
              {query_code}
            </code>
          </div>
        )}
        
        {/* 테이블 헤더 */}
        <div className="px-3 py-2 bg-gray-100 dark:bg-gray-700 border-b">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              데이터 결과
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {rows.length}개 행 표시 {total_rows > rows.length && `(총 ${total_rows}개)`}
            </span>
          </div>
        </div>
        
        {/* 테이블 본문 */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                {columns.map((column: string, index: number) => (
                  <th 
                    key={index}
                    className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300 border-b"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row: any, rowIndex: number) => (
                <tr 
                  key={rowIndex}
                  className={rowIndex % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-750'}
                >
                  {columns.map((column: string, colIndex: number) => (
                    <td 
                      key={colIndex}
                      className="px-3 py-2 text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-600"
                    >
                      {typeof row[column] === 'number' ? 
                        row[column].toLocaleString() : 
                        String(row[column] || '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  /**
   * 차트 렌더링
   */
  const renderChart = () => {
    if (!message.metadata?.chartData) return null;

    const { chartData } = message.metadata;
    
    return (
      <div className="mt-4">
        <ChartDisplay
          type={chartData.type}
          data={chartData.data}
          {...(chartData.title && { title: chartData.title })}
          options={chartData.options}
          width={500}
          height={300}
        />
      </div>
    );
  };

  /**
   * 메시지 내용 렌더링
   * - 일반 텍스트
   * - 마크다운 (향후 구현)
   * - 코드 블록
   * - 데이터 테이블
   */
  const renderContent = () => {
    // 오류 메시지 처리
    if (message.error) {
      return (
        <div className="text-red-600">
          <div className="font-medium mb-1">오류가 발생했습니다</div>
          <div className="text-sm opacity-80">{message.error}</div>
          {message.role === 'user' && (
            <button
              onClick={handleRetry}
              className="mt-2 text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded"
            >
              다시 시도
            </button>
          )}
        </div>
      );
    }

    // 로딩 상태
    if (message.isLoading) {
      return (
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-current rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
          <span className="text-sm opacity-70">처리 중...</span>
        </div>
      );
    }

    // 메시지 내용 파싱하여 table_data와 chart_data 추출
    const parseMessageData = () => {
      let tableData = null;
      let chartData = null;
      
      // 스트리밍 메시지에서 JSON 데이터 추출 시도
      try {
        const content = message.content.replace(/\[TABLE_DATA\][\s\S]*?\[\/TABLE_DATA\]/, '').replace(/\[CHART_DATA\][\s\S]*?\[\/CHART_DATA\]/, '');
        
        // 테이블 데이터 추출
        const tableMatch = content.match(/```table\n([\s\S]*?)\n```/);
        if (tableMatch && tableMatch[1]) {
          tableData = JSON.parse(tableMatch[1]);
        }

        // 차트 데이터 추출
        const chartMatch = content.match(/```chart\n([\s\S]*?)\n```/);
        if (chartMatch && chartMatch[1]) {
          chartData = JSON.parse(chartMatch[1]);
        }
      } catch (e) {
        // JSON 파싱 실패 시 무시
      }
      
      // metadata에서도 확인
      if (!tableData && (message.metadata as any)?.tableData) {
        tableData = (message.metadata as any).tableData;
      }
      if (!chartData && message.metadata?.chartData) {
        chartData = message.metadata.chartData;
      }
      
      // 디버깅용 로깅
      console.log('🔍 MessageBubble parseMessageData 실행:', {
        messageId: message.id,
        messageRole: message.role,
        hasMetadata: !!message.metadata,
        metadataChartData: message.metadata?.chartData,
        tableData,
        chartData
      });
      
      if (chartData) {
        console.log('📊 차트 데이터 발견!', {
          messageId: message.id,
          chartData,
          chartType: chartData.type,
          chartTitle: chartData.title,
          labelsCount: chartData.data?.labels?.length,
          datasetsCount: chartData.data?.datasets?.length
        });
      }
      
      return { tableData, chartData };
    };

    const { tableData, chartData } = parseMessageData();
    const hasVisualData = tableData || chartData;
    
    console.log('🎨 렌더링 상태 확인:', {
      messageId: message.id,
      hasVisualData,
      tableData: !!tableData,
      chartData: !!chartData,
      chartDataType: chartData?.type
    });

    // 일반 텍스트 메시지 및 시각화 데이터
    return (
      <div>
        <div className="whitespace-pre-wrap">
          {message.content.replace(/\[TABLE_DATA\][\s\S]*?\[\/TABLE_DATA\]/, '').replace(/\[CHART_DATA\][\s\S]*?\[\/CHART_DATA\]/, '')}
        </div>
        
        {hasVisualData && (
          <div className={`mt-4 ${tableData && chartData ? 'grid grid-cols-1 lg:grid-cols-2 gap-4' : ''}`}>
            {tableData && (
              <div className="order-1">
                <QueryResultTable
                  data={tableData}
                  title="쿼리 결과"
                  showQuery={true}
                  className="w-full"
                />
              </div>
            )}
            {chartData && (
              <div className="order-2">
                <QueryResultChart
                  data={chartData}
                  title={chartData.title || "데이터 시각화"}
                  width={500}
                  height={300}
                  className="w-full"
                />
              </div>
            )}
          </div>
        )}
        
        {/* 기존 차트 렌더링 (백워드 호환성) */}
        {!hasVisualData && renderChart()}
      </div>
    );
  };

  /**
   * 툴 상태 렌더링
   */
  const renderToolStatus = () => {
    if (!message.metadata?.toolStatus || message.metadata.toolStatus.length === 0) return null;

    return (
      <div className="mt-2 space-y-1">
        <div className="text-xs font-medium opacity-70">🔧 도구 실행 상태:</div>
        {message.metadata.toolStatus.map((tool, index) => (
          <div key={index} className="flex items-center space-x-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${
              tool.status === 'running' ? 'bg-yellow-500 animate-pulse' :
              tool.status === 'completed' ? 'bg-green-500' :
              'bg-red-500'
            }`}></div>
            <span className="font-medium">{tool.tool_name}</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${
              tool.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
              tool.status === 'completed' ? 'bg-green-100 text-green-800' :
              'bg-red-100 text-red-800'
            }`}>
              {tool.status === 'running' ? '실행 중' :
               tool.status === 'completed' ? '완료' : '오류'}
            </span>
          </div>
        ))}
      </div>
    );
  };

  /**
   * 메타데이터 렌더링 (쿼리 타입, 실행 시간 등)
   */
  const renderMetadata = () => {
    if (!message.metadata) return null;

    const { queryType, dataSource, executionTime } = message.metadata;

    return (
      <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap gap-2 text-xs opacity-70">

          {queryType && (
            <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
              {queryType}
            </span>
          )}
          {dataSource && (
            <span className="bg-green-100 text-green-800 px-2 py-1 rounded">
              {dataSource}
            </span>
          )}
          {executionTime && (
            <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded">
              {executionTime}ms
            </span>
          )}
        </div>
      </div>
    );
  };

  /**
   * 액션 버튼들 렌더링
   */
  const renderActions = () => {
    if (!showActions) return null;

    return (
      <div className={`
        absolute top-0 ${isUser ? 'left-0 -translate-x-full' : 'right-0 translate-x-full'}
        flex items-center space-x-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border p-1
        transition-all duration-200 ease-in-out
      `}>
        {/* 복사 버튼 */}
        <button
          onClick={handleCopy}
          className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-500 hover:text-gray-700"
          title="복사"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>

        {/* 재시도 버튼 (사용자 메시지만) */}
        {message.role === 'user' && (
          <button
            onClick={handleRetry}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-500 hover:text-gray-700"
            title="다시 시도"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}
      </div>
    );
  };

  // ============================================================================
  // 메인 렌더링
  // ============================================================================

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : isSystem ? 'justify-center' : 'justify-start'} ${isLast ? 'mb-4' : ''}`}
      onMouseEnter={() => {
        setIsHovered(true);
        setShowActions(true);
      }}
      onMouseLeave={() => {
        setIsHovered(false);
        setShowActions(false);
      }}
    >
      <div className="relative">
        {/* 메시지 버블 */}
        <div className={bubbleClasses}>
          {/* 메시지 내용 */}
          {renderContent()}
          
          {/* 툴 실행 상태 */}
          {renderToolStatus()}
          
          {/* 메타데이터 */}
          {renderMetadata()}
          
          {/* 시간 표시 */}
          {showTimestamp && (
            <div className={`
              text-xs mt-1 opacity-60
              ${isUser ? 'text-right' : 'text-left'}
            `}>
              {new Date(message.timestamp).toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          )}
        </div>

        {/* 액션 버튼들 */}
        {renderActions()}
      </div>
    </div>
  );
};

export default MessageBubble; 