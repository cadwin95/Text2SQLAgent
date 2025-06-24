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
  const [expandedColumns, setExpandedColumns] = useState<Set<string>>(new Set());

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
      
      if (data && data.tables) {
        setSchema(data);
        setConnectionStatus('connected');
      } else {
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
      // 테이블 닫을 때 컬럼도 닫기
      setExpandedColumns(prev => new Set([...prev].filter(col => !col.startsWith(tableName))));
    } else {
      newExpanded.add(tableName);
    }
    setExpandedTables(newExpanded);
  };

  const toggleColumns = (tableName: string) => {
    const columnsKey = `${tableName}_columns`;
    const newExpanded = new Set(expandedColumns);
    if (newExpanded.has(columnsKey)) {
      newExpanded.delete(columnsKey);
    } else {
      newExpanded.add(columnsKey);
    }
    setExpandedColumns(newExpanded);
  };

  const handleTableClick = (tableName: string, schemaName?: string) => {
    const fullTableName = schemaName && schemaName !== 'default' ? `${schemaName}.${tableName}` : tableName;
    onTableSelect?.(fullTableName);
    const query = `SELECT * FROM ${fullTableName} LIMIT 10;`;
    onQueryGenerate?.(query);
  };

  const getColumnIcon = (column: any) => {
    if (column.primary_key) return '🔑';
    if (column.type.toLowerCase().includes('int')) return '#';
    if (column.type.toLowerCase().includes('varchar') || column.type.toLowerCase().includes('text')) return 'Aa';
    if (column.type.toLowerCase().includes('date') || column.type.toLowerCase().includes('time')) return '📅';
    if (column.type.toLowerCase().includes('bool')) return '☑';
    return '○';
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected': return <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>;
      case 'disconnected': return <div className="w-1.5 h-1.5 bg-red-400 rounded-full"></div>;
      case 'loading': return <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse"></div>;
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-900 text-xs">
      {/* Compact Header */}
      <div className="px-2 py-1.5 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center space-x-1.5">
          <span className="text-gray-400">📂</span>
          <span className="text-gray-300 font-medium text-xs">EXPLORER</span>
        </div>
        <div className="flex items-center space-x-1">
          {getConnectionIcon()}
          <button
            onClick={loadSchema}
            className="text-gray-400 hover:text-white transition-colors p-0.5 rounded hover:bg-gray-700"
            title="새로고침"
            disabled={loading || !currentConnection}
          >
            {loading ? '⟳' : '🔄'}
          </button>
        </div>
      </div>

      {/* Tree View */}
      <div className="flex-1 overflow-y-auto">
        {!currentConnection ? (
          <div className="p-4 text-center text-gray-500">
            <div className="text-lg mb-1">🔌</div>
            <div className="text-xs">연결이 필요합니다</div>
          </div>
        ) : loading ? (
          <div className="p-4 text-center text-gray-500">
            <div className="text-lg mb-1">⏳</div>
            <div className="text-xs">로딩 중...</div>
          </div>
        ) : !schema || schema.tables.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <div className="text-lg mb-1">📂</div>
            <div className="text-xs">테이블이 없습니다</div>
          </div>
        ) : (
          <div className="p-1">
            {/* Database Root */}
            <div className="py-0.5 px-1 text-gray-400 text-xs font-medium flex items-center">
              <span className="mr-1">🗄️</span>
              <span className="truncate">{currentConnection.name}</span>
              <span className="ml-1 text-gray-600">({schema.tables.length})</span>
            </div>
            
            {/* Tables Tree - 스키마별 그룹화 */}
            <div className="ml-2">
              {/* 스키마별로 그룹화 */}
              {(() => {
                const tablesBySchema = schema.tables.reduce((acc, table) => {
                  const schemaName = (table as any).schema || 'default';
                  if (!acc[schemaName]) {
                    acc[schemaName] = [];
                  }
                  acc[schemaName].push(table);
                  return acc;
                }, {} as Record<string, typeof schema.tables>);

                return Object.entries(tablesBySchema).map(([schemaName, tables]) => (
                  <div key={schemaName}>
                    {/* 스키마 노드 - 여러 스키마가 있을 때만 표시 */}
                    {Object.keys(tablesBySchema).length > 1 && (
                      <div 
                        className="flex items-center py-0.5 px-1 hover:bg-gray-800 rounded cursor-pointer text-purple-400"
                        onClick={() => {
                          const schemaKey = `schema_${schemaName}`;
                          const newExpanded = new Set(expandedTables);
                          if (newExpanded.has(schemaKey)) {
                            newExpanded.delete(schemaKey);
                            // 스키마 닫을 때 해당 스키마의 모든 테이블도 닫기
                            tables.forEach(table => {
                              newExpanded.delete(table.name);
                              setExpandedColumns(prev => new Set([...prev].filter(col => !col.startsWith(table.name))));
                            });
                          } else {
                            newExpanded.add(schemaKey);
                          }
                          setExpandedTables(newExpanded);
                        }}
                      >
                        <span className="text-gray-400 mr-1 text-xs">
                          {expandedTables.has(`schema_${schemaName}`) ? '▼' : '▶'}
                        </span>
                        <span className="text-purple-400 mr-1">📁</span>
                        <span className="text-xs text-purple-300">
                          {schemaName}
                        </span>
                        <span className="ml-1 text-gray-600 text-xs">
                          ({tables.length})
                        </span>
                      </div>
                    )}
                    
                    {/* 테이블 목록 - 스키마가 펼쳐져 있거나 단일 스키마일 때만 표시 */}
                    {(Object.keys(tablesBySchema).length === 1 || expandedTables.has(`schema_${schemaName}`)) && (
                      <div className={Object.keys(tablesBySchema).length > 1 ? "ml-3" : ""}>
                        {tables.map((table) => (
                          <div key={`${schemaName}.${table.name}`}>
                            {/* Table Node */}
                            <div className="group">
                              <div 
                                className="flex items-center py-0.5 px-1 hover:bg-gray-800 rounded cursor-pointer"
                                onClick={() => toggleTable(table.name)}
                              >
                                <span className="text-gray-400 mr-1 text-xs">
                                  {expandedTables.has(table.name) ? '▼' : '▶'}
                                </span>
                                <span className="text-blue-400 mr-1">📄</span>
                                <span 
                                  className="text-gray-300 text-xs truncate hover:text-white"
                                  onDoubleClick={() => handleTableClick(table.name, (table as any).schema)}
                                  title={`${(table as any).schema ? `${(table as any).schema}.` : ''}${table.name} (더블클릭: SELECT 쿼리)`}
                                >
                                  {table.name}
                                </span>
                                {table.row_count !== undefined && (
                                  <span className="ml-1 text-gray-600 text-xs">
                                    ({table.row_count > 1000 ? `${Math.round(table.row_count/1000)}k` : table.row_count})
                                  </span>
                                )}
                              </div>
                              
                              {/* Table Content */}
                              {expandedTables.has(table.name) && (
                                <div className="ml-4 border-l border-gray-700 pl-2">
                                  {/* Columns Section */}
                                  <div>
                                    <div 
                                      className="flex items-center py-0.5 px-1 hover:bg-gray-800 rounded cursor-pointer"
                                      onClick={() => toggleColumns(table.name)}
                                    >
                                      <span className="text-gray-400 mr-1 text-xs">
                                        {expandedColumns.has(`${table.name}_columns`) ? '▼' : '▶'}
                                      </span>
                                      <span className="text-green-400 mr-1">📋</span>
                                      <span className="text-gray-400 text-xs">columns ({table.columns.length})</span>
                                    </div>
                                    
                                    {/* Column List */}
                                    {expandedColumns.has(`${table.name}_columns`) && (
                                      <div className="ml-4 border-l border-gray-700 pl-2">
                                        {table.columns.map((column) => (
                                          <div key={column.name} className="flex items-center py-0.5 px-1 text-xs">
                                            <span className="mr-1">
                                              {column.primary_key ? '🔑' : 
                                               column.type.includes('int') || column.type.includes('number') || column.type.includes('decimal') || column.type.includes('float') ? '#' :
                                               column.type.includes('varchar') || column.type.includes('text') || column.type.includes('char') ? 'Aa' :
                                               column.type.includes('date') || column.type.includes('time') ? '📅' :
                                               column.type.includes('bool') ? '☑' : '○'}
                                            </span>
                                            <span className="text-gray-300 mr-1">{column.name}</span>
                                            <span className="text-gray-500 mr-1">{column.type}</span>
                                            {column.primary_key && <span className="text-yellow-400 text-xs mr-1">PK</span>}
                                            {!column.nullable && <span className="text-red-400 text-xs">NN</span>}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                  
                                  {/* Quick Actions */}
                                  <div className="flex items-center py-0.5 px-1 space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                      onClick={() => handleTableClick(table.name, (table as any).schema)}
                                      className="text-xs text-blue-400 hover:text-blue-300 px-1"
                                      title="SELECT 쿼리"
                                    >
                                      SELECT
                                    </button>
                                    <button
                                      onClick={() => {
                                        const columnNames = table.columns.map(col => col.name).join(', ');
                                        const placeholders = table.columns.map(() => '?').join(', ');
                                        const fullTableName = (table as any).schema ? `${(table as any).schema}.${table.name}` : table.name;
                                        const query = `INSERT INTO ${fullTableName} (${columnNames}) VALUES (${placeholders});`;
                                        onQueryGenerate?.(query);
                                      }}
                                      className="text-xs text-green-400 hover:text-green-300 px-1"
                                      title="INSERT 쿼리"
                                    >
                                      INSERT
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ));
              })()}
            </div>
          </div>
        )}
      </div>

      {/* Compact Footer */}
      <div className="px-2 py-1 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
        <span>{currentConnection?.type?.toUpperCase() || 'NO'} DB</span>
        <div className="flex items-center space-x-1">
          {connectionStatus === 'connected' && schema && (
            <span>{schema.tables.length} tables</span>
          )}
        </div>
      </div>
    </div>
  );
} 