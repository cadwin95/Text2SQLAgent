'use client';

import React, { useState, useEffect } from 'react';
import { DatabaseConnection } from '@/types/database';
import { DATABASE_CONFIGS } from '@/utils/database-configs';
import { safelyCallDatabaseAPI } from '@/utils/database-api';
import DatabaseConnectionModal from './DatabaseConnectionModal';

interface ConnectionManagerProps {
  isOpen: boolean;
  onClose: () => void;
  onConnectionSelect: (connection: DatabaseConnection) => void;
  currentConnection?: DatabaseConnection | null;
}

export default function ConnectionManager({ 
  isOpen, 
  onClose, 
  onConnectionSelect, 
  currentConnection 
}: ConnectionManagerProps) {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConnection, setEditingConnection] = useState<DatabaseConnection | null>(null);
  const [connectingId, setConnectingId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadConnections();
    }
  }, [isOpen]);

  const loadConnections = async () => {
    try {
      const connections = await safelyCallDatabaseAPI.getConnections();
      setConnections(connections);
    } catch (error) {
      console.error('연결 목록 로드 실패:', error);
      setConnections([]);
    }
  };

  const handleAddConnection = () => {
    setEditingConnection(null);
    setShowConnectionModal(true);
  };

  const handleEditConnection = (connection: DatabaseConnection) => {
    setEditingConnection(connection);
    setShowConnectionModal(true);
  };

  const handleSaveConnection = async (connection: DatabaseConnection) => {
    try {
      if (editingConnection) {
        // 편집 모드: 백엔드와 localStorage 모두 업데이트
        try {
          // 백엔드에 업데이트 요청
          await safelyCallDatabaseAPI.updateConnection(connection);
          console.log('✅ 백엔드에 연결 정보 업데이트됨');
        } catch (error) {
          console.warn('⚠️ 백엔드 업데이트 실패, localStorage에만 저장됨:', error);
        }
        
        // UI 상태 업데이트
        const updatedConnections = connections.map(c => 
          c.id === connection.id ? connection : c
        );
        setConnections(updatedConnections);
        
        // localStorage에 저장
        try {
          localStorage.setItem('database-connections', JSON.stringify(updatedConnections));
          console.log('🔄 연결 정보가 localStorage에 업데이트되었습니다.');
        } catch (error) {
          console.error('localStorage 저장 실패:', error);
        }
      } else {
        // 새 연결 생성
        const newConnection = await safelyCallDatabaseAPI.createConnection(connection);
        setConnections(prev => [...prev, newConnection]);
      }
    } catch (error) {
      console.error('연결 저장 실패:', error);
    }
  };

  const handleDeleteConnection = async (connectionId: string) => {
    if (!confirm('이 연결을 삭제하시겠습니까?')) return;

    try {
      await safelyCallDatabaseAPI.deleteConnection(connectionId);
      setConnections(prev => prev.filter(c => c.id !== connectionId));
    } catch (error) {
      console.error('연결 삭제 실패:', error);
    }
  };

  const handleConnect = async (connection: DatabaseConnection) => {
    setConnectingId(connection.id);
    
    try {
      // 연결 활성화
      await safelyCallDatabaseAPI.activateConnection(connection.id);
      
      // UI 상태 업데이트
      const updatedConnections = connections.map(c => ({
        ...c,
        isActive: c.id === connection.id,
        lastConnected: c.id === connection.id ? new Date() : c.lastConnected
      }));
      setConnections(updatedConnections);
      
      onConnectionSelect({ ...connection, isActive: true, lastConnected: new Date() });
      onClose();
    } catch (error) {
      console.error('연결 실패:', error);
    } finally {
      setConnectingId(null);
    }
  };

  const handleDisconnect = async (connection: DatabaseConnection) => {
    try {
      const updatedConnections = connections.map(c => 
        c.id === connection.id ? { ...c, isActive: false } : c
      );
      setConnections(updatedConnections);
      
      // localStorage에도 반영
      try {
        localStorage.setItem('database-connections', JSON.stringify(updatedConnections));
      } catch (error) {
        console.error('localStorage 저장 실패:', error);
      }
    } catch (error) {
      console.error('연결 해제 실패:', error);
    }
  };

  const getConnectionStatusIcon = (connection: DatabaseConnection) => {
    if (connectingId === connection.id) {
      return <div className="w-3 h-3 bg-yellow-400 rounded-full animate-pulse"></div>;
    }
    if (connection.isActive) {
      return <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>;
    }
    return <div className="w-3 h-3 bg-gray-500 rounded-full"></div>;
  };

  const formatLastConnected = (date?: Date) => {
    if (!date) return '연결된 적 없음';
    
    const now = new Date();
    const diff = now.getTime() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}일 전`;
    if (hours > 0) return `${hours}시간 전`;
    if (minutes > 0) return `${minutes}분 전`;
    return '방금 전';
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-lg w-full max-w-5xl max-h-[80vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-700">
            <div>
              <h2 className="text-xl font-semibold text-white">데이터베이스 연결 관리</h2>
              <p className="text-sm text-gray-400 mt-1">
                {connections.length}개의 연결 • {connections.filter(c => c.isActive).length}개 활성
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleAddConnection}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              >
                ➕ 새 연결
              </button>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-white transition-colors text-xl"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Connection List */}
          <div className="overflow-y-auto" style={{ height: '500px' }}>
            {connections.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <div className="text-4xl mb-4">🔌</div>
                  <h3 className="text-lg font-medium mb-2">연결이 없습니다</h3>
                  <p className="text-sm mb-4">새로운 데이터베이스 연결을 추가하세요</p>
                  <button
                    onClick={handleAddConnection}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                  >
                    첫 번째 연결 추가
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6">
                <div className="grid gap-4">
                  {connections.map((connection) => {
                    const config = DATABASE_CONFIGS[connection.type];
                    const isCurrentConnection = currentConnection?.id === connection.id;
                    
                    return (
                      <div
                        key={connection.id}
                        className={`p-4 border rounded-lg transition-colors ${
                          isCurrentConnection
                            ? 'border-blue-500 bg-blue-900/20'
                            : connection.isActive
                            ? 'border-green-600 bg-green-900/20'
                            : 'border-gray-600 bg-gray-750 hover:bg-gray-700'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <div className="text-2xl">{config.icon}</div>
                            <div>
                              <div className="flex items-center space-x-2">
                                <h3 className="font-medium text-white">{connection.name}</h3>
                                {getConnectionStatusIcon(connection)}
                                {isCurrentConnection && (
                                  <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded">
                                    현재 연결
                                  </span>
                                )}
                              </div>
                              <div className="text-sm text-gray-400 mt-1">
                                {config.label} • {connection.host}:{connection.port} • {connection.database}
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                마지막 연결: {formatLastConnected(connection.lastConnected)}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center space-x-2">
                            {connection.isActive ? (
                              <button
                                onClick={() => handleDisconnect(connection)}
                                className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm transition-colors"
                              >
                                연결 해제
                              </button>
                            ) : (
                              <button
                                onClick={() => handleConnect(connection)}
                                disabled={connectingId === connection.id}
                                className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded text-sm transition-colors"
                              >
                                {connectingId === connection.id ? '연결 중...' : '연결'}
                              </button>
                            )}
                            
                            <button
                              onClick={() => handleEditConnection(connection)}
                              className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded text-sm transition-colors"
                            >
                              수정
                            </button>
                            
                            <button
                              onClick={() => handleDeleteConnection(connection.id)}
                              className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm transition-colors"
                            >
                              삭제
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Connection Modal */}
      <DatabaseConnectionModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        onSave={handleSaveConnection}
        editConnection={editingConnection}
      />
    </>
  );
} 