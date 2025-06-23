'use client';

import React, { useState, useRef, useImperativeHandle, forwardRef } from 'react';

interface QueryEditorProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
  onQueryExecute: (query: string) => void;
  onQuerySet?: (query: string) => void;
}

interface QueryTab {
  id: string;
  title: string;
  content: string;
  saved: boolean;
}

interface QueryEditorRef {
  setQuery: (query: string) => void;
  getQuery: () => string;
}

const QueryEditor = forwardRef<QueryEditorRef, QueryEditorProps>(
  ({ activeTab, onTabChange, onQueryExecute, onQuerySet }, ref) => {
    const [tabs, setTabs] = useState<QueryTab[]>([
      { id: 'query1', title: 'Query 1', content: 'SELECT * FROM users;', saved: true },
      { id: 'query2', title: 'Query 2', content: '-- 새로운 쿼리를 작성하세요', saved: true }
    ]);
    
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const activeTabData = tabs.find(tab => tab.id === activeTab) || tabs[0];

    // Imperative handle for parent components
    useImperativeHandle(ref, () => ({
      setQuery: (query: string) => {
        handleContentChange(query);
      },
      getQuery: () => {
        return activeTabData?.content || '';
      }
    }));

    const handleContentChange = (content: string) => {
      setTabs(tabs.map(tab => 
        tab.id === activeTab 
          ? { ...tab, content, saved: false }
          : tab
      ));
      onQuerySet?.(content);
    };

    const handleExecuteQuery = () => {
      if (activeTabData?.content?.trim()) {
        onQueryExecute(activeTabData.content);
      }
    };

    const handleNewTab = () => {
      const newTabId = `query${tabs.length + 1}`;
      const newTab: QueryTab = {
        id: newTabId,
        title: `Query ${tabs.length + 1}`,
        content: '-- 새로운 쿼리를 작성하세요',
        saved: true
      };
      setTabs([...tabs, newTab]);
      onTabChange(newTabId);
    };

    const handleCloseTab = (tabId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      if (tabs.length > 1) {
        const newTabs = tabs.filter(tab => tab.id !== tabId);
        setTabs(newTabs);
        
        if (activeTab === tabId) {
          onTabChange(newTabs[0]?.id || '');
        }
      }
    };

    const formatSQL = () => {
      if (!activeTabData) return;
      
      const content = activeTabData.content;
      const formatted = content
        .replace(/\bSELECT\b/gi, '\nSELECT')
        .replace(/\bFROM\b/gi, '\nFROM')
        .replace(/\bWHERE\b/gi, '\nWHERE')
        .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
        .replace(/\bORDER BY\b/gi, '\nORDER BY')
        .replace(/\bJOIN\b/gi, '\nJOIN')
        .replace(/\bINNER JOIN\b/gi, '\nINNER JOIN')
        .replace(/\bLEFT JOIN\b/gi, '\nLEFT JOIN')
        .replace(/\bRIGHT JOIN\b/gi, '\nRIGHT JOIN')
        .replace(/\bUNION\b/gi, '\nUNION')
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .join('\n');
      
      handleContentChange(formatted);
    };

    const insertQueryAtCursor = (query: string) => {
      if (!textareaRef.current) return;
      
      const textarea = textareaRef.current;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const currentContent = activeTabData?.content || '';
      
      const newContent = currentContent.substring(0, start) + 
                        query + 
                        currentContent.substring(end);
      
      handleContentChange(newContent);
      
      // 커서 위치 조정
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + query.length;
        textarea.focus();
      }, 0);
    };

    if (!activeTabData) {
      return <div>Loading...</div>;
    }

    return (
      <div className="flex-1 flex flex-col">
        {/* Tab Bar */}
        <div className="flex items-center bg-gray-800 border-b border-gray-700">
          <div className="flex-1 flex items-center overflow-x-auto">
            {tabs.map(tab => (
              <div
                key={tab.id}
                className={`flex items-center px-4 py-2 border-r border-gray-700 cursor-pointer min-w-0 ${
                  activeTab === tab.id 
                    ? 'bg-gray-900 text-white' 
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
                onClick={() => onTabChange(tab.id)}
              >
                <span className="truncate mr-2">
                  {tab.saved ? tab.title : `${tab.title} •`}
                </span>
                {tabs.length > 1 && (
                  <button
                    className="text-gray-400 hover:text-white ml-1"
                    onClick={(e) => handleCloseTab(tab.id, e)}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
          
          <button
            className="px-3 py-2 text-gray-400 hover:text-white hover:bg-gray-700"
            onClick={handleNewTab}
            title="New Tab"
          >
            +
          </button>
        </div>

        {/* Editor Toolbar */}
        <div className="flex items-center justify-between bg-gray-850 px-4 py-2 border-b border-gray-700">
          <div className="flex items-center space-x-2">
            <button
              className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium"
              onClick={handleExecuteQuery}
              title="Execute Query (F5)"
            >
              ▶ Run
            </button>
            
            <button
              className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded text-sm"
              onClick={formatSQL}
              title="Format SQL (Ctrl+Shift+F)"
            >
              Format
            </button>

            <div className="w-px h-4 bg-gray-600 mx-2" />

            <button
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
              onClick={() => insertQueryAtCursor('SELECT * FROM ')}
              title="Insert SELECT"
            >
              SELECT
            </button>

            <button
              className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm"
              onClick={() => insertQueryAtCursor('INSERT INTO table_name (column1, column2) VALUES (?, ?);')}
              title="Insert INSERT"
            >
              INSERT
            </button>
          </div>
          
          <div className="text-xs text-gray-400">
            SQL Editor • Line {activeTabData.content.split('\n').length}
          </div>
        </div>

        {/* Code Editor */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            className="w-full h-full p-4 bg-gray-900 text-green-400 font-mono text-sm resize-none focus:outline-none"
            value={activeTabData.content}
            onChange={(e) => handleContentChange(e.target.value)}
            placeholder="-- SQL 쿼리를 작성하세요..."
            style={{
              fontFamily: 'Consolas, "Courier New", monospace',
              lineHeight: '1.5',
              fontSize: '14px',
              paddingLeft: '4rem'
            }}
            onKeyDown={(e) => {
              // F5로 실행
              if (e.key === 'F5') {
                e.preventDefault();
                handleExecuteQuery();
              }
              // Ctrl+Enter로 실행
              if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                handleExecuteQuery();
              }
              // Tab 입력 지원
              if (e.key === 'Tab') {
                e.preventDefault();
                const textarea = e.target as HTMLTextAreaElement;
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const value = textarea.value;
                const newValue = value.substring(0, start) + '  ' + value.substring(end);
                handleContentChange(newValue);
                
                // 커서 위치 조정
                setTimeout(() => {
                  textarea.selectionStart = textarea.selectionEnd = start + 2;
                }, 0);
              }
            }}
          />
          
          {/* Line Numbers */}
          <div className="absolute left-0 top-0 w-12 h-full bg-gray-800 border-r border-gray-700 text-gray-500 text-xs font-mono pt-4 pl-2 pointer-events-none">
            {activeTabData.content.split('\n').map((_, index) => (
              <div key={index} style={{ lineHeight: '1.5', fontSize: '14px' }}>
                {index + 1}
              </div>
            ))}
          </div>
        </div>

        {/* Status Bar */}
        <div className="h-6 bg-gray-800 border-t border-gray-700 flex items-center justify-between px-4 text-xs text-gray-400">
          <div>
            Characters: {activeTabData.content.length} | Lines: {activeTabData.content.split('\n').length}
          </div>
          <div>
            SQL • UTF-8
          </div>
        </div>
      </div>
    );
  }
);

QueryEditor.displayName = 'QueryEditor';

export default QueryEditor; 