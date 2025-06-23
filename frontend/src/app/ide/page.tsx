'use client';

import React, { useState, useRef } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import TopBar from '@/components/ide/TopBar';
import DBExplorer from '@/components/ide/DBExplorer';
import QueryEditor from '@/components/ide/QueryEditor';
import AIPanel from '@/components/ide/AIPanel';
import ResultPanel from '@/components/ide/ResultPanel';
import ConnectionManager from '@/components/ide/ConnectionManager';
import { DatabaseConnection } from '@/types/database';

/**
 * SQL IDE 메인 페이지 - 3패널 구조
 * 
 * Layout:
 * ┌─────────────────────────────────────────────────────────────┐
 * │                    Top Bar                                  │
 * ├─────────────────────────────────────────────────────────────┤
 * │ DB Explorer ║ Query Editor (resizable) ║ AI Assistant      │
 * ├─────────────────────────────────────────────────────────────┤
 * │ Result Panel (resizable height)                            │
 * └─────────────────────────────────────────────────────────────┘
 */
export default function IDEPage() {
  const [activeTab, setActiveTab] = useState<string>('query1');
  const [queryResults, setQueryResults] = useState<any>(null);
  const [consoleMessages, setConsoleMessages] = useState<string[]>([]);
  const [activeResultTab, setActiveResultTab] = useState<'table' | 'chart' | 'console'>('table');
  
  // 패널 상태 관리
  const [showDBExplorer, setShowDBExplorer] = useState(true);
  const [showAIPanel, setShowAIPanel] = useState(true);
  const [showResultPanel, setShowResultPanel] = useState(true);

  // 연결 관리 상태
  const [showConnectionManager, setShowConnectionManager] = useState(false);
  const [currentConnection, setCurrentConnection] = useState<DatabaseConnection | null>(null);

  // QueryEditor ref
  const queryEditorRef = useRef<{
    setQuery: (query: string) => void;
    getQuery: () => string;
  }>(null);

  const handleQueryExecute = async (query: string) => {
    if (!currentConnection) {
      setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ❌ 연결된 데이터베이스가 없습니다. 먼저 데이터베이스에 연결하세요.`]);
      setActiveResultTab('console');
      setShowResultPanel(true);
      return;
    }

    try {
      setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] 쿼리 실행 중...`]);
      setConsoleMessages(prev => [...prev, `SQL: ${query}`]);
      setConsoleMessages(prev => [...prev, `Connection: ${currentConnection.name} (${currentConnection.type})`]);
      
      // API 호출
      const response = await fetch('/api/database/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question: query,
          connectionId: currentConnection.id
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setQueryResults(result);
        setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ✅ ${result.result?.row_count || 0}행 조회됨`]);
        setActiveResultTab('table');
        setShowResultPanel(true);
      } else {
        setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ❌ 오류: ${result.error}`]);
        setActiveResultTab('console');
        setShowResultPanel(true);
      }
    } catch (error) {
      setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ❌ 네트워크 오류: ${error}`]);
      setActiveResultTab('console');
      setShowResultPanel(true);
    }
  };

  const handleAIQuery = async (question: string) => {
    if (!currentConnection) {
      setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ❌ 연결된 데이터베이스가 없습니다. 먼저 데이터베이스에 연결하세요.`]);
      setActiveResultTab('console');
      setShowResultPanel(true);
      return null;
    }

    try {
      setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] AI 쿼리: ${question}`]);
      setConsoleMessages(prev => [...prev, `Connection: ${currentConnection.name} (${currentConnection.type})`]);
      
      const response = await fetch('/api/database/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question,
          connectionId: currentConnection.id
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setQueryResults(result);
        setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ✅ AI가 생성한 SQL 실행됨`]);
        setActiveResultTab('table');
        setShowResultPanel(true);
        
        // 생성된 SQL을 에디터에 표시
        if (result.sql_query && queryEditorRef.current) {
          queryEditorRef.current.setQuery(result.sql_query);
        }
        return result.sql_query;
      } else {
        setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ❌ AI 쿼리 실패: ${result.error}`]);
        setActiveResultTab('console');
        setShowResultPanel(true);
        return null;
      }
    } catch (error) {
      setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ❌ AI 쿼리 오류: ${error}`]);
      setActiveResultTab('console');
      setShowResultPanel(true);
      return null;
    }
  };

  const handleDBQueryGenerate = (query: string) => {
    setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] 📂 DB Explorer에서 쿼리 생성: ${query}`]);
    
    // QueryEditor에 쿼리 설정
    if (queryEditorRef.current) {
      queryEditorRef.current.setQuery(query);
    }
  };

  const handleConnectionSelect = (connection: DatabaseConnection) => {
    setCurrentConnection(connection);
    setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] 🔌 ${connection.name}에 연결됨 (${connection.type})`]);
    
    // DB Explorer 새로고침
    // DBExplorer 컴포넌트에서 연결 변경을 감지하도록 해야 함
  };

  const getCurrentConnectionDisplay = () => {
    if (!currentConnection) return undefined;
    return `${currentConnection.name} (${currentConnection.type.toUpperCase()})`;
  };

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* Top Bar */}
      <TopBar 
        onToggleDBExplorer={() => setShowDBExplorer(!showDBExplorer)}
        onToggleAIPanel={() => setShowAIPanel(!showAIPanel)}
        onToggleResultPanel={() => setShowResultPanel(!showResultPanel)}
        onOpenConnectionManager={() => setShowConnectionManager(true)}
        showDBExplorer={showDBExplorer}
        showAIPanel={showAIPanel}
        showResultPanel={showResultPanel}
        currentConnection={getCurrentConnectionDisplay()}
      />
      
      {/* Main Layout with Resizable Panels */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup direction="vertical">
          {/* Top Section: DB Explorer + Query Editor + AI Panel */}
          <Panel defaultSize={60} minSize={30}>
            <PanelGroup direction="horizontal">
              {/* DB Explorer Panel */}
              {showDBExplorer && (
                <>
                  <Panel defaultSize={20} minSize={15} maxSize={35}>
                    <DBExplorer 
                      onTableSelect={(tableName) => {
                        setConsoleMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] 📂 테이블 선택: ${tableName}`]);
                      }}
                      onQueryGenerate={handleDBQueryGenerate}
                      currentConnection={currentConnection}
                    />
                  </Panel>
                  <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-col-resize" />
                </>
              )}
              
              {/* Query Editor */}
              <Panel 
                defaultSize={showDBExplorer && showAIPanel ? 55 : showDBExplorer || showAIPanel ? 75 : 100} 
                minSize={40}
              >
                <QueryEditor
                  ref={queryEditorRef}
                  activeTab={activeTab}
                  onTabChange={setActiveTab}
                  onQueryExecute={handleQueryExecute}
                />
              </Panel>
              
              {/* AI Panel */}
              {showAIPanel && (
                <>
                  <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-col-resize" />
                  <Panel defaultSize={25} minSize={20} maxSize={40}>
                    <AIPanel 
                      onAIQuery={handleAIQuery}
                      currentConnection={currentConnection}
                    />
                  </Panel>
                </>
              )}
            </PanelGroup>
          </Panel>
          
          {/* Bottom Section: Result Panel */}
          {showResultPanel && (
            <>
              <PanelResizeHandle className="h-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-row-resize" />
              <Panel defaultSize={40} minSize={20} maxSize={60}>
                <ResultPanel
                  queryResults={queryResults}
                  consoleMessages={consoleMessages}
                  activeTab={activeResultTab}
                  onTabChange={setActiveResultTab}
                  onClearConsole={() => setConsoleMessages([])}
                />
              </Panel>
            </>
          )}
        </PanelGroup>
      </div>

      {/* Connection Manager Modal */}
      <ConnectionManager
        isOpen={showConnectionManager}
        onClose={() => setShowConnectionManager(false)}
        onConnectionSelect={handleConnectionSelect}
        currentConnection={currentConnection}
      />
    </div>
  );
} 