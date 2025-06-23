'use client';

import React from 'react';

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
    if (!queryResults || !queryResults.result || !queryResults.result.data) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <div className="text-4xl mb-4">📊</div>
            <div>쿼리를 실행하면 결과가 여기에 표시됩니다</div>
          </div>
        </div>
      );
    }

    const { data, columns } = queryResults.result;

    return (
      <div className="h-full overflow-auto">
        <div className="p-4">
          <div className="mb-4 text-sm text-gray-400">
            총 {data.length}행 조회됨 • 실행 시간: {queryResults.execution_time}ms
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full bg-gray-800 rounded-lg overflow-hidden">
              <thead className="bg-gray-700">
                <tr>
                  {columns.map((column: string, index: number) => (
                    <th 
                      key={index}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {data.map((row: any[], rowIndex: number) => (
                  <tr 
                    key={rowIndex}
                    className="hover:bg-gray-750 transition-colors"
                  >
                    {row.map((cell: any, cellIndex: number) => (
                      <td 
                        key={cellIndex}
                        className="px-4 py-3 text-sm text-gray-300"
                      >
                        {cell === null ? (
                          <span className="text-gray-500 italic">NULL</span>
                        ) : typeof cell === 'object' ? (
                          JSON.stringify(cell)
                        ) : (
                          String(cell)
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
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