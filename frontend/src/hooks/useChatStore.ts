// hooks/useChatStore.ts
// =====================
// Zustand 기반 채팅 상태 관리
// - 채팅 세션, 메시지, 사용자 설정 관리
// - 로컬 스토리지 연동으로 데이터 영속성
// - 타입 안전한 상태 관리

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ChatStore, ChatSession, Message, UserPreferences } from '@/types';

/**
 * 기본 사용자 설정
 */
const defaultPreferences: UserPreferences = {
  theme: 'system',
  language: 'ko',
  autoSave: true,
  notifications: {
    enabled: true,
    sound: true,
    desktop: false,
  },
  display: {
    fontSize: 'medium',
    density: 'comfortable',
    showTimestamps: true,
  },
};

/**
 * 채팅 상태 관리 스토어
 * 
 * 주요 기능:
 * 1. 채팅 세션 관리 (생성, 삭제, 전환)
 * 2. 메시지 관리 (추가, 수정, 삭제)
 * 3. 실시간 연결 상태 관리
 * 4. 사용자 설정 관리
 * 5. 로컬 스토리지 자동 동기화
 */
export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      // ========================================================================
      // 상태
      // ========================================================================
      sessions: [],
      currentSessionId: null,
      isConnected: false,
      isTyping: false,
      userPreferences: defaultPreferences,

      // ========================================================================
      // 세션 관리 액션
      // ========================================================================

      /**
       * 새 채팅 세션 생성
       */
      createSession: (title?: string) => {
        const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newSession: ChatSession = {
          id: sessionId,
          title: title || `채팅 ${new Date().toLocaleDateString('ko-KR')}`,
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          isActive: true,
        };

        set((state) => ({
          sessions: [...state.sessions, newSession],
          currentSessionId: sessionId,
        }));

        return sessionId;
      },

      /**
       * 채팅 세션 삭제
       */
      deleteSession: (sessionId: string) => {
        set((state) => {
          const filteredSessions = state.sessions.filter(s => s.id !== sessionId);
          let newCurrentSessionId = state.currentSessionId;
          
          if (state.currentSessionId === sessionId) {
            newCurrentSessionId = filteredSessions.length > 0 && filteredSessions[0] 
              ? filteredSessions[0].id 
              : null;
          }

          return {
            sessions: filteredSessions,
            currentSessionId: newCurrentSessionId,
          };
        });
      },

      /**
       * 현재 활성 세션 설정
       */
      setCurrentSession: (sessionId: string) => {
        set((state) => {
          // 세션이 존재하는지 확인
          const sessionExists = state.sessions.some(s => s.id === sessionId);
          if (!sessionExists) return state;

          // 모든 세션을 비활성화하고 선택된 세션만 활성화
          const updatedSessions = state.sessions.map(session => ({
            ...session,
            isActive: session.id === sessionId,
            updatedAt: session.id === sessionId ? new Date() : session.updatedAt,
          }));

          return {
            sessions: updatedSessions,
            currentSessionId: sessionId,
          };
        });
      },

      // ========================================================================
      // 메시지 관리 액션
      // ========================================================================

      /**
       * 메시지 추가
       */
      addMessage: (sessionId: string, message: Message) => {
        set((state) => {
          const updatedSessions = state.sessions.map(session => {
            if (session.id === sessionId) {
              return {
                ...session,
                messages: [...session.messages, message],
                updatedAt: new Date(),
              };
            }
            return session;
          });

          return { sessions: updatedSessions };
        });
      },

      /**
       * 메시지 수정
       */
      updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => {
        set((state) => {
          const updatedSessions = state.sessions.map(session => {
            if (session.id === sessionId) {
              const updatedMessages = session.messages.map(msg => {
                if (msg.id === messageId) {
                  return { ...msg, ...updates };
                }
                return msg;
              });

              return {
                ...session,
                messages: updatedMessages,
                updatedAt: new Date(),
              };
            }
            return session;
          });

          return { sessions: updatedSessions };
        });
      },

      // ========================================================================
      // 연결 상태 관리
      // ========================================================================

      /**
       * 연결 상태 설정
       */
      setConnectionStatus: (status: boolean) => {
        set({ isConnected: status });
      },

      /**
       * 타이핑 상태 설정
       */
      setTypingStatus: (isTyping: boolean) => {
        set({ isTyping });
      },

      // ========================================================================
      // 사용자 설정 관리
      // ========================================================================

      /**
       * 사용자 설정 업데이트
       */
      updatePreferences: (preferences: Partial<UserPreferences>) => {
        set((state) => ({
          userPreferences: {
            ...state.userPreferences,
            ...preferences,
          },
        }));
      },

      // ========================================================================
      // 유틸리티 액션
      // ========================================================================

      /**
       * 모든 채팅 기록 삭제
       */
      clearHistory: () => {
        set({
          sessions: [],
          currentSessionId: null,
        });
      },
    }),
    {
      name: 'text2sql-chat-store', // 로컬 스토리지 키
      partialize: (state) => ({
        // 영속화할 상태만 선택 (연결 상태, 타이핑 상태는 제외)
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
        userPreferences: state.userPreferences,
      }),
    }
  )
);

// ============================================================================
// 유틸리티 훅들
// ============================================================================

/**
 * 현재 활성 세션 가져오기
 */
export const useCurrentSession = () => {
  const { sessions, currentSessionId } = useChatStore();
  return sessions.find(session => session.id === currentSessionId) || null;
};

/**
 * 현재 세션의 메시지들 가져오기
 */
export const useCurrentMessages = () => {
  const currentSession = useCurrentSession();
  return currentSession?.messages || [];
};

/**
 * 세션 통계 정보
 */
export const useSessionStats = (sessionId?: string) => {
  const { sessions, currentSessionId } = useChatStore();
  const targetSessionId = sessionId || currentSessionId;
  const session = sessions.find(s => s.id === targetSessionId);

  if (!session) {
    return {
      messageCount: 0,
      userMessageCount: 0,
      assistantMessageCount: 0,
      createdAt: null,
      lastMessageAt: null,
    };
  }

  const userMessages = session.messages.filter(m => m.role === 'user');
  const assistantMessages = session.messages.filter(m => m.role === 'assistant');
  const lastMessage = session.messages[session.messages.length - 1];

  return {
    messageCount: session.messages.length,
    userMessageCount: userMessages.length,
    assistantMessageCount: assistantMessages.length,
    createdAt: session.createdAt,
    lastMessageAt: lastMessage?.timestamp || null,
  };
}; 