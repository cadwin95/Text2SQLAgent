'use client';

import React, { useState, useEffect } from 'react';
import { DatabaseConnection } from '@/types/database';
import { databaseAPI } from '@/utils/database-api';

interface DBExplorerProps {
  onTableSelect?: (tableName: string) => void;
  onQueryGenerate?: (query: string) => void;
  currentConnection?: DatabaseConnection | null;
}

interface DatabaseSchema {
  tables: {
    name: string;
    columns: Array<{
      name: string;
      type: string;
      nullable: boolean;
      primary_key: boolean;
    }>;
    row_count?: number;
  }[];
}

type ConnectionStatus = 'connected' | 'disconnected' | 'loading';

export default function DBExplorer({ onTableSelect, onQueryGenerate, currentConnection }: DBExplorerProps) {
  const [schema, setSchema] = useState<DatabaseSchema | null>(null);
  const [loading, setLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (currentConnection?.isActive) {
      loadSchema();
    } else {
      setSchema(null);
      setConnectionStatus('disconnected');
    }
  }, [currentConnection]);

  const loadSchema = async () => {
    if (!currentConnection) {
      setConnectionStatus('disconnected');
      return;
    }

    setLoading(true);
    try {
      const data = await databaseAPI.getSchema(currentConnection.id);
      console.log('📥 스키마 데이터 수신:', data);
      
      // 백엔드에서 직접 스키마 객체를 반환함 (data.schema가 아님)
      if (data && data.tables) {
        setSchema(data);
        setConnectionStatus('connected');
        console.log('✅ 스키마 설정 완료, 테이블 수:', data.tables.length);
      } else {
        console.warn('⚠️ 스키마 데이터가 올바르지 않음:', data);
        setConnectionStatus('disconnected');
      }
    } catch (error) {
      console.error('스키마 로드 실패:', error);
      setConnectionStatus('disconnected');
    } finally {
      setLoading(false);
    }
  };

  const toggleTable = (tableName: string) => {
    const newExpanded = new Set(expandedTables);
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName);
    } else {
      newExpanded.add(tableName);
    }
    setExpandedTables(newExpanded);
  };

  const handleTableClick = (tableName: string) => {
    onTableSelect?.(tableName);
    const query = `SELECT * FROM ${tableName} LIMIT 10;`;
    onQueryGenerate?.(query);
  };

  const generateInsertQuery = (tableName: string, columns: any[]) => {
    const columnNames = columns.map(col => col.name).join(', ');
    const placeholders = columns.map(() => '?').join(', ');
    const query = `INSERT INTO ${tableName} (${columnNames}) VALUES (${placeholders});`;
    onQueryGenerate?.(query);
  };

  const generateUpdateQuery = (tableName: string, columns: any[]) => {
    const setClause = columns.filter(col => !col.primary_key).map(col => `${col.name} = ?`).join(', ');
    const primaryKey = columns.find(col => col.primary_key);
    const whereClause = primaryKey ? `${primaryKey.name} = ?` : 'id = ?';
    const query = `UPDATE ${tableName} SET ${setClause} WHERE ${whereClause};`;
    onQueryGenerate?.(query);
  };

  const getColumnIcon = (column: any) => {
    if (column.primary_key) return '🔑';
    if (column.type.toLowerCase().includes('int')) return '🔢';
    if (column.type.toLowerCase().includes('varchar') || column.type.toLowerCase().includes('text')) return '📝';
    if (column.type.toLowerCase().includes('date') || column.type.toLowerCase().includes('time')) return '📅';
    if (column.type.toLowerCase().includes('bool')) return '☑️';
    return '📄';
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected': return <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>;
      case 'disconnected': return <div className="w-2 h-2 bg-red-400 rounded-full"></div>;
      case 'loading': return <div className="w-2 h-2 bg-yellow-400 rounded-full animate-spin"></div>;
    }
  };

  const getConnectionDisplayInfo = () => {
    if (!currentConnection) {
      return {
        title: '연결 없음',
        subtitle: '데이터베이스에 연결하세요'
      };
    }
    
    return {
      title: currentConnection.name,
      subtitle: `${currentConnection.type.toUpperCase()} • ${currentConnection.host || 'localhost'}`
    };
  };

  const connectionInfo = getConnectionDisplayInfo();

  return (
    <div className="h-full flex flex-col bg-gray-800">
      {/* Header */}
      <div className="p-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center">
            <span className="mr-2">📂</span>
            DB Explorer
          </h3>
          <div className="flex items-center space-x-2">
            {getConnectionIcon()}
            <button
              onClick={loadSchema}
              className="text-xs text-gray-400 hover:text-white transition-colors"
              title="새로고침"
              disabled={loading || !currentConnection}
            >
              {loading ? '⟳' : '🔄'}
            </button>
          </div>
        </div>
        <div className="text-xs text-gray-400 mt-1">
          <div>{connectionInfo.title}</div>
          <div className="text-gray-500">{connectionInfo.subtitle}</div>
        </div>
      </div>

      {/* Connection Status */}
      {!currentConnection ? (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          <div className="text-center">
            <div className="text-4xl mb-4">🔌</div>
            <h3 className="text-lg font-medium mb-2">연결 필요</h3>
            <p className="text-sm mb-4">데이터베이스에 연결하여<br />스키마를 탐색하세요</p>
            <div className="text-xs text-gray-500">
              상단 메뉴 → Database → Connection Manager
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Connection Actions */}
          <div className="p-2 border-b border-gray-700">
            <div className="grid grid-cols-2 gap-1">
              <button
                className="p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded text-xs font-medium transition-colors"
                onClick={loadSchema}
                disabled={loading}
              >
                🔄 새로고침
              </button>
              
              <button
                className="p-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded text-xs font-medium transition-colors"
                onClick={() => onQueryGenerate?.('SHOW TABLES;')}
                disabled={!currentConnection?.isActive}
              >
                📋 테이블 목록
              </button>
            </div>
          </div>

          {/* Database Trees */}
          <div className="flex-1 overflow-y-auto p-2">
            {loading ? (
              <div className="flex items-center justify-center h-32 text-gray-400">
                <div className="text-center">
                  <div className="text-2xl mb-2">⏳</div>
                  <div className="text-xs">스키마 로딩 중...</div>
                </div>
              </div>
            ) : connectionStatus === 'disconnected' ? (
              <div className="flex items-center justify-center h-32 text-gray-400">
                <div className="text-center">
                  <div className="text-2xl mb-2">❌</div>
                  <div className="text-xs">데이터베이스 연결 실패</div>
                  <button
                    onClick={loadSchema}
                    className="mt-2 px-2 py-1 bg-gray-600 hover:bg-gray-700 text-white text-xs rounded"
                  >
                    재연결
                  </button>
                </div>
              </div>
            ) : !schema || schema.tables.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-gray-400">
                <div className="text-center">
                  <div className="text-2xl mb-2">📂</div>
                  <div className="text-xs">테이블이 없습니다</div>
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                {schema.tables.map((table) => (
                  <div key={table.name} className="border border-gray-700 rounded">
                    {/* Table Header */}
                    <div 
                      className="flex items-center justify-between p-2 bg-gray-750 hover:bg-gray-700 cursor-pointer transition-colors"
                      onClick={() => toggleTable(table.name)}
                    >
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className="text-xs">
                          {expandedTables.has(table.name) ? '📂' : '📁'}
                        </span>
                        <span className="text-sm font-medium text-white truncate">
                          {table.name}
                        </span>
                        {table.row_count !== undefined && (
                          <span className="text-xs text-gray-400">
                            ({table.row_count}행)
                          </span>
                        )}
                      </div>
                      <div className="flex space-x-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTableClick(table.name);
                          }}
                          className="text-xs text-blue-400 hover:text-blue-300"
                          title="SELECT 쿼리 생성"
                        >
                          👁️
                        </button>
                      </div>
                    </div>

                    {/* Table Details */}
                    {expandedTables.has(table.name) && (
                      <div className="bg-gray-800">
                        {/* Quick Actions */}
                        <div className="px-2 py-1 border-b border-gray-700">
                          <div className="flex space-x-1">
                            <button
                              onClick={() => handleTableClick(table.name)}
                              className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
                              title="SELECT 쿼리"
                            >
                              SELECT
                            </button>
                            <button
                              onClick={() => generateInsertQuery(table.name, table.columns)}
                              className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded"
                              title="INSERT 쿼리"
                            >
                              INSERT
                            </button>
                            <button
                              onClick={() => generateUpdateQuery(table.name, table.columns)}
                              className="px-2 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-xs rounded"
                              title="UPDATE 쿼리"
                            >
                              UPDATE
                            </button>
                          </div>
                        </div>

                        {/* Columns */}
                        <div className="p-2 space-y-1">
                          {table.columns.map((column, index) => (
                            <div 
                              key={index}
                              className="flex items-center justify-between p-1 hover:bg-gray-700 rounded text-xs"
                            >
                              <div className="flex items-center space-x-2 min-w-0">
                                <span>{getColumnIcon(column)}</span>
                                <span className="text-white font-medium truncate">
                                  {column.name}
                                </span>
                              </div>
                              <div className="flex items-center space-x-1 text-gray-400">
                                <span className="text-xs">{column.type}</span>
                                {column.primary_key && <span title="Primary Key">PK</span>}
                                {!column.nullable && <span title="Not Null">NN</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Footer */}
      <div className="p-2 border-t border-gray-700 text-xs text-gray-400">
        <div className="flex items-center justify-between">
          <span>{currentConnection?.type || 'No'} Database</span>
          <span>{connectionStatus === 'connected' ? '연결됨' : '연결 안됨'}</span>
        </div>
      </div>
    </div>
  );
} 