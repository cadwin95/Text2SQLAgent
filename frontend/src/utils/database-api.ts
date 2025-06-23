// utils/database-api.ts
// ====================
// Database API 전용 통신 유틸리티
// - 백엔드 데이터베이스 관리 API와 통신
// - 연결 관리, 스키마 조회, 쿼리 실행 등

import axios from 'axios';
import { DatabaseConnection } from '@/types/database';

// Database API 클라이언트 설정
const databaseApiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
databaseApiClient.interceptors.request.use(
  (config) => {
    console.log('🔗 Database API 요청:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('❌ Database API 요청 오류:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터
databaseApiClient.interceptors.response.use(
  (response) => {
    console.log('✅ Database API 응답:', response.status, response.config.url);
    console.log('✅ 응답 데이터:', response.data);
    return response;
  },
  (error) => {
    console.error('❌ Database API 응답 오류:', error.response?.status, error.response?.data);
    if (error.response?.data && typeof error.response.data === 'string' && error.response.data.includes('<!DOCTYPE')) {
      console.error('❌ HTML 응답 감지 - 백엔드 연결 문제:', error.response.data.substring(0, 200));
      console.error('❌ 요청 URL:', error.config?.url);
      console.error('❌ Base URL:', error.config?.baseURL);
    }
    return Promise.reject(error);
  }
);

/**
 * 연결 관련 API
 */
export const databaseAPI = {
  // 연결 목록 조회
  getConnections: async (): Promise<DatabaseConnection[]> => {
    try {
      const response = await databaseApiClient.get('/api/database/connections');
      return response.data;
    } catch (error) {
      console.error('연결 목록 조회 실패:', error);
      throw error;
    }
  },

  // 연결 생성
  createConnection: async (connection: Omit<DatabaseConnection, 'id'>): Promise<DatabaseConnection> => {
    try {
      const response = await databaseApiClient.post('/api/database/connections', connection);
      return response.data;
    } catch (error) {
      console.error('연결 생성 실패:', error);
      throw error;
    }
  },

  // 연결 업데이트
  updateConnection: async (id: string, connection: Partial<DatabaseConnection>): Promise<DatabaseConnection> => {
    try {
      const response = await databaseApiClient.put(`/api/database/connections/${id}`, connection);
      return response.data;
    } catch (error) {
      console.error('연결 업데이트 실패:', error);
      throw error;
    }
  },

  // 연결 삭제
  deleteConnection: async (id: string): Promise<void> => {
    try {
      await databaseApiClient.delete(`/api/database/connections/${id}`);
    } catch (error) {
      console.error('연결 삭제 실패:', error);
      throw error;
    }
  },

  // 연결 활성화
  activateConnection: async (id: string): Promise<void> => {
    try {
      await databaseApiClient.put(`/api/database/connections/${id}/activate`);
    } catch (error) {
      console.error('연결 활성화 실패:', error);
      throw error;
    }
  },

  // 연결 테스트
  testConnection: async (connection: any): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await databaseApiClient.post('/api/database/connections/test', connection);
      return response.data;
    } catch (error) {
      console.error('연결 테스트 실패:', error);
      throw error;
    }
  },

  // 스키마 조회
  getSchema: async (connectionId?: string): Promise<any> => {
    try {
      const url = connectionId 
        ? `/api/database/schema?connectionId=${connectionId}`
        : '/api/database/schema';
      const response = await databaseApiClient.get(url);
      return response.data;
    } catch (error) {
      console.error('스키마 조회 실패:', error);
      throw error;
    }
  },

  // 쿼리 실행
  executeQuery: async (query: string, connectionId?: string): Promise<any> => {
    try {
      const response = await databaseApiClient.post('/api/database/query', {
        query,
        connection_id: connectionId
      });
      return response.data;
    } catch (error) {
      console.error('쿼리 실행 실패:', error);
      throw error;
    }
  },

  // 헬스 체크
  healthCheck: async (): Promise<boolean> => {
    try {
      const response = await databaseApiClient.get('/api/database/health');
      return response.status === 200;
    } catch (error) {
      console.error('Database API 헬스 체크 실패:', error);
      return false;
    }
  },

  // 백엔드 연결 테스트 (루트 경로)
  testBackendConnection: async (): Promise<boolean> => {
    try {
      console.log('🔍 백엔드 연결 테스트 시작...');
      const response = await databaseApiClient.get('/');
      console.log('✅ 백엔드 루트 응답:', response.data);
      return true;
    } catch (error) {
      console.error('❌ 백엔드 연결 실패:', error);
      return false;
    }
  }
};

/**
 * localStorage 백업 함수들
 */
export const localStorageBackup = {
  // 연결 정보 저장
  saveConnections: (connections: DatabaseConnection[]): void => {
    try {
      localStorage.setItem('database-connections', JSON.stringify(connections));
      console.log('🔄 localStorage에 연결 정보 저장됨');
    } catch (error) {
      console.error('localStorage 저장 실패:', error);
    }
  },

  // 연결 정보 로드
  loadConnections: (): DatabaseConnection[] => {
    try {
      const stored = localStorage.getItem('database-connections');
      if (stored) {
        const connections = JSON.parse(stored);
        console.log('📥 localStorage에서 연결 정보 로드됨');
        return connections;
      }
    } catch (error) {
      console.error('localStorage 로드 실패:', error);
    }
    return [];
  },

  // 활성 연결 설정
  setActiveConnection: (connectionId: string): void => {
    try {
      const connections = localStorageBackup.loadConnections();
      const updatedConnections = connections.map(conn => ({
        ...conn,
        isActive: conn.id === connectionId,
        lastConnected: conn.id === connectionId ? new Date() : conn.lastConnected
      }));
      localStorageBackup.saveConnections(updatedConnections);
    } catch (error) {
      console.error('활성 연결 설정 실패:', error);
    }
  }
};

/**
 * 통합 Database API (백엔드 + localStorage 백업)
 */
export const safelyCallDatabaseAPI = {
  // 연결 목록 조회 (백엔드 우선, 실패시 localStorage)
  getConnections: async (): Promise<DatabaseConnection[]> => {
    try {
      return await databaseAPI.getConnections();
    } catch (error) {
      console.warn('백엔드 API 실패, localStorage에서 로드:', error);
      return localStorageBackup.loadConnections();
    }
  },

  // 연결 생성 (localStorage 우선 저장, 백엔드는 백그라운드)
  createConnection: async (connection: Omit<DatabaseConnection, 'id'>): Promise<DatabaseConnection> => {
    const newConnection: DatabaseConnection = {
      ...connection,
      id: `conn-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date(),
      isActive: false
    };

    // localStorage에 즉시 저장
    const connections = localStorageBackup.loadConnections();
    connections.push(newConnection);
    localStorageBackup.saveConnections(connections);

    // 백엔드에 백그라운드로 저장 시도
    try {
      await databaseAPI.createConnection(newConnection);
      console.log('✅ 백엔드에도 성공적으로 저장됨');
    } catch (error) {
      console.warn('⚠️ 백엔드 저장 실패, localStorage에만 저장됨:', error);
    }

    return newConnection;
  },

  // 연결 활성화 (localStorage 우선, 백엔드는 백그라운드)
  activateConnection: async (connectionId: string): Promise<void> => {
    // localStorage에서 즉시 활성화
    localStorageBackup.setActiveConnection(connectionId);

    // 백엔드에 백그라운드로 활성화 시도
    try {
      await databaseAPI.activateConnection(connectionId);
      console.log('✅ 백엔드에서도 활성화됨');
    } catch (error) {
      console.warn('⚠️ 백엔드 활성화 실패, localStorage에서만 처리됨:', error);
    }
  },

  // 연결 삭제 (localStorage 우선, 백엔드는 백그라운드)
  deleteConnection: async (connectionId: string): Promise<void> => {
    // localStorage에서 즉시 삭제
    const connections = localStorageBackup.loadConnections();
    const filteredConnections = connections.filter(conn => conn.id !== connectionId);
    localStorageBackup.saveConnections(filteredConnections);

    // 백엔드에서 백그라운드로 삭제 시도
    try {
      await databaseAPI.deleteConnection(connectionId);
      console.log('✅ 백엔드에서도 삭제됨');
    } catch (error) {
      console.warn('⚠️ 백엔드 삭제 실패, localStorage에서만 삭제됨:', error);
    }
  }
}; 