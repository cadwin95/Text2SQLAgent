// types/index.ts
// ===============
// 전역 TypeScript 타입 정의
// - 채팅 메시지, API 응답, 컴포넌트 Props 등 타입 정의
// - Backend API와 일치하는 데이터 구조 정의
// - 타입 안전성 보장 및 개발 생산성 향상

// ============================================================================
// 채팅 관련 타입
// ============================================================================

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  isLoading?: boolean;
  error?: string;
  metadata?: {
    queryType?: 'text2sql' | 'analysis' | 'visualization';
    dataSource?: string;
    executionTime?: number;
    isStreaming?: boolean;
    toolStatus?: Array<{
      tool_name: string;
      status: 'running' | 'completed' | 'error';
      message?: string;
    }>;
    chartData?: {
      type: 'line' | 'bar' | 'pie' | 'doughnut';
      title?: string;
      data: {
        labels: string[];
        datasets: Array<{
          label: string;
          data: number[];
          backgroundColor?: string | string[];
          borderColor?: string;
          borderWidth?: number;
          tension?: number;
        }>;
      };
      options?: any;
    };
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;
}

// ============================================================================
// API 관련 타입 (Backend 연동)
// ============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface ChatRequest {
  message: string;
  sessionId?: string;
  context?: {
    previousMessages?: Message[];
    userPreferences?: UserPreferences;
  };
}

export interface ChatResponse {
  message: Message;
  sessionId: string;
  suggestions?: string[];
  dataVisualization?: {
    type: 'table' | 'chart' | 'graph';
    data: any;
    config?: any;
  };
}

// ============================================================================
// 데이터 분석 관련 타입
// ============================================================================

export interface DataFrameResult {
  columns: string[];
  rows: any[][];
  shape: [number, number];
  dtypes?: Record<string, string>;
  summary?: {
    totalRows: number;
    totalColumns: number;
    memoryUsage?: string;
  };
}

export interface AnalysisResult {
  query: string;
  result: DataFrameResult;
  executionTime: number;
  error?: string;
  visualization?: {
    type: 'bar' | 'line' | 'pie' | 'scatter' | 'table';
    config: any;
  };
}

// ============================================================================
// 사용자 설정 관련 타입
// ============================================================================

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: 'ko' | 'en';
  autoSave: boolean;
  notifications: {
    enabled: boolean;
    sound: boolean;
    desktop: boolean;
  };
  display: {
    fontSize: 'small' | 'medium' | 'large';
    density: 'compact' | 'comfortable' | 'spacious';
    showTimestamps: boolean;
  };
}

// ============================================================================
// Socket.io 실시간 통신 타입
// ============================================================================

export interface SocketEvents {
  // 클라이언트 → 서버
  'chat:send': (data: ChatRequest) => void;
  'chat:typing:start': (data: { sessionId: string }) => void;
  'chat:typing:stop': (data: { sessionId: string }) => void;
  'session:join': (sessionId: string) => void;
  'session:leave': (sessionId: string) => void;

  // 서버 → 클라이언트
  'chat:message': (data: ChatResponse) => void;
  'chat:typing': (data: { sessionId: string; isTyping: boolean }) => void;
  'chat:error': (error: string) => void;
  'session:created': (sessionId: string) => void;
  'connection:status': (status: 'connected' | 'disconnected' | 'reconnecting') => void;
}

// ============================================================================
// 컴포넌트 Props 타입
// ============================================================================

export interface ChatContainerProps {
  sessionId?: string;
  initialMessages?: Message[];
  onMessageSend?: (message: string) => void;
  onSessionChange?: (sessionId: string) => void;
}

export interface MessageBubbleProps {
  message: Message;
  isLast?: boolean;
  showTimestamp?: boolean;
  onRetry?: ((messageId: string) => void) | undefined;
  onCopy?: ((content: string) => void) | undefined;
}

export interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  suggestions?: string[];
  isLoading?: boolean;
}

// ============================================================================
// 상태 관리 타입 (Zustand)
// ============================================================================

export interface ChatStore {
  // 상태
  sessions: ChatSession[];
  currentSessionId: string | null;
  isConnected: boolean;
  isTyping: boolean;
  userPreferences: UserPreferences;

  // 액션
  addMessage: (sessionId: string, message: Message) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void;
  createSession: (title?: string) => string;
  deleteSession: (sessionId: string) => void;
  setCurrentSession: (sessionId: string) => void;
  setConnectionStatus: (status: boolean) => void;
  setTypingStatus: (isTyping: boolean) => void;
  updatePreferences: (preferences: Partial<UserPreferences>) => void;
  clearHistory: () => void;
}

// ============================================================================
// 유틸리티 타입
// ============================================================================

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T = any> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export type ThemeMode = 'light' | 'dark' | 'system';

export type MessageRole = 'user' | 'assistant' | 'system';

// ============================================================================
// 확장 가능한 타입 (향후 기능)
// ============================================================================

export interface FileUpload {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
  uploadedAt: Date;
}

export interface ChatPlugin {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  config?: Record<string, any>;
}

export interface ExportOptions {
  format: 'json' | 'csv' | 'pdf' | 'markdown';
  includeTimestamps: boolean;
  includeMetadata: boolean;
  dateRange?: {
    start: Date;
    end: Date;
  };
} 