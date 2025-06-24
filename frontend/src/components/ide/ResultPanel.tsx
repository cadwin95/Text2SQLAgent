'use client';

import React from 'react';
import QueryResultTable from '../QueryResultTable';

interface ResultPanelProps {
  queryResults: any;
  consoleMessages: string[];
  activeTab: 'table' | 'chart' | 'console';
  onTabChange: (tab: 'table' | 'chart' | 'console') => void;
  onClearConsole: () => void;
}

export default function ResultPanel({ 
  queryResults, 
  consoleMessages, 
  activeTab, 
  onTabChange, 
  onClearConsole 
}: ResultPanelProps) {
  
  const renderTableView = () => {
    if (!queryResults || !queryResults.success || !queryResults.data) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <div className="text-4xl mb-4">📊</div>
            <div>쿼리를 실행하면 결과가 여기에 표시됩니다</div>
            {queryResults && !queryResults.success && queryResults.error && (
              <div className="mt-4 text-red-400 text-sm">
                오류: {queryResults.error}
              </div>
            )}
          </div>
        </div>
      );
    }

    // 백엔드 응답 구조에 맞게 직접 접근
    const { data, columns } = queryResults;
    
    // 데이터가 이미 딕셔너리 배열 형태로 오므로 그대로 사용
    const tableData = {
      columns: columns,
      rows: data, // 이미 올바른 형식
      total_rows: queryResults.row_count || data.length,
      query_code: queryResults.query || 'SELECT * FROM table'
    };

    return (
      <div className="h-full">
        <QueryResultTable 
          data={tableData}
          title="쿼리 결과"
          showQuery={true}
          className="bg-gray-800 text-white border-gray-700"
        />
      </div>
    );
  };

  const renderChartView = () => {
    if (!queryResults || !queryResults.result || !queryResults.result.data) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <div className="text-4xl mb-4">📈</div>
            <div>차트 기능은 개발 중입니다</div>
            <div className="text-sm mt-2">숫자 데이터가 포함된 결과를 실행하면 차트로 시각화됩니다</div>
          </div>
        </div>
      );
    }

    return (
      <div className="h-full p-4">
        <div className="bg-gray-800 rounded-lg p-6 h-full flex items-center justify-center">
          <div className="text-center text-gray-400">
            <div className="text-4xl mb-4">🚧</div>
            <div className="text-lg mb-2">차트 뷰 구현 예정</div>
            <div className="text-sm">
              데이터 시각화 기능이 곧 추가될 예정입니다
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderConsoleView = () => {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="text-sm text-gray-400">
            Console Log ({consoleMessages.length} messages)
          </div>
          <button
            onClick={onClearConsole}
            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-xs rounded transition-colors"
          >
            Clear
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
          {consoleMessages.length === 0 ? (
            <div className="text-gray-500 italic">콘솔이 비어있습니다</div>
          ) : (
            consoleMessages.map((message, index) => (
              <div 
                key={index}
                className={`mb-1 ${
                  message.includes('❌') 
                    ? 'text-red-400' 
                    : message.includes('✅')
                    ? 'text-green-400'
                    : 'text-gray-300'
                }`}
              >
                {message}
              </div>
            ))
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Tab Bar */}
      <div className="flex items-center bg-gray-800 border-b border-gray-700">
        {[
          { id: 'table', label: '📊 Table', desc: '쿼리 결과' },
          { id: 'chart', label: '📈 Chart', desc: '차트 뷰' },
          { id: 'console', label: '🖥️ Console', desc: '실행 로그' }
        ].map((tab) => (
          <button
            key={tab.id}
            className={`flex items-center px-4 py-3 border-r border-gray-700 transition-colors ${
              activeTab === tab.id
                ? 'bg-gray-900 text-white border-b-2 border-blue-500'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
            onClick={() => onTabChange(tab.id as 'table' | 'chart' | 'console')}
          >
            <span className="text-sm font-medium mr-2">{tab.label}</span>
            <span className="text-xs text-gray-500">{tab.desc}</span>
          </button>
        ))}
        
        {/* Result Summary */}
        <div className="ml-auto px-4 py-3 text-xs text-gray-400">
          {queryResults && queryResults.result && (
            <span>
              {queryResults.sql_query && `SQL: ${queryResults.sql_query.substring(0, 50)}...`}
            </span>
          )}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'table' && renderTableView()}
        {activeTab === 'chart' && renderChartView()}
        {activeTab === 'console' && renderConsoleView()}
      </div>
    </div>
  );
} 