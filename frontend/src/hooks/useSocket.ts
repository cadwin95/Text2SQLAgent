// hooks/useSocket.ts
// ==================
// Socket.io 클라이언트 훅
// - 실시간 통신 연결 관리
// - 메시지 송수신, 이벤트 처리
// - 자동 재연결, 오류 처리

import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { ChatRequest } from '@/types';

interface UseSocketOptions {
  url?: string;
  autoConnect?: boolean;
  reconnection?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
}

interface UseSocketReturn {
  socket: Socket | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  sendMessage: (data: ChatRequest) => Promise<void>;
  joinSession: (sessionId: string) => void;
  leaveSession: (sessionId: string) => void;
  connect: () => void;
  disconnect: () => void;
}

/**
 * Socket.io 클라이언트 훅
 * 
 * 주요 기능:
 * 1. Socket.io 연결 관리 (연결, 재연결, 해제)
 * 2. 실시간 메시지 송수신
 * 3. 세션 참여/떠나기
 * 4. 연결 상태 관리
 * 5. 오류 처리 및 재시도
 * 6. 타이핑 상태 전송
 */
export const useSocket = (options: UseSocketOptions = {}): UseSocketReturn => {
  const {
    url = process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:8000',
    autoConnect = true,
    reconnection = true,
    reconnectionAttempts = 5,
    reconnectionDelay = 1000,
  } = options;

  // ============================================================================
  // 상태 관리
  // ============================================================================
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<Socket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // ============================================================================
  // Socket 연결 관리
  // ============================================================================

  /**
   * Socket 연결
   */
  const connect = () => {
    if (socketRef.current?.connected) return;

    setIsConnecting(true);
    setError(null);

    try {
      const newSocket = io(url, {
        autoConnect: false,
        reconnection,
        reconnectionAttempts,
        reconnectionDelay,
        transports: ['websocket', 'polling'],
      });

      // 연결 성공
      newSocket.on('connect', () => {
        console.log('Socket connected:', newSocket.id);
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
      });

      // 연결 해제
      newSocket.on('disconnect', (reason) => {
        console.log('Socket disconnected:', reason);
        setIsConnected(false);
        setIsConnecting(false);
        
        // 서버에서 연결을 끊은 경우가 아니면 재연결 시도
        if (reason !== 'io server disconnect' && reconnection) {
          setError('연결이 끊어졌습니다. 재연결을 시도합니다...');
        }
      });

      // 연결 오류
      newSocket.on('connect_error', (err) => {
        console.error('Socket connection error:', err);
        setIsConnected(false);
        setIsConnecting(false);
        setError(`연결 오류: ${err.message}`);
      });

      // 재연결 시도
      newSocket.on('reconnect_attempt', (attemptNumber) => {
        console.log(`재연결 시도 ${attemptNumber}/${reconnectionAttempts}`);
        setIsConnecting(true);
        setError(`재연결 시도 중... (${attemptNumber}/${reconnectionAttempts})`);
      });

      // 재연결 성공
      newSocket.on('reconnect', (attemptNumber) => {
        console.log(`재연결 성공 (${attemptNumber}번째 시도)`);
        setError(null);
      });

      // 재연결 실패
      newSocket.on('reconnect_failed', () => {
        console.error('재연결 실패');
        setIsConnecting(false);
        setError('서버에 연결할 수 없습니다. 나중에 다시 시도해주세요.');
      });

      socketRef.current = newSocket;
      
      // 연결 시작
      newSocket.connect();

    } catch (err) {
      console.error('Socket 초기화 오류:', err);
      setIsConnecting(false);
      setError('Socket 초기화에 실패했습니다.');
    }
  };

  /**
   * Socket 연결 해제
   */
  const disconnect = () => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
      setIsConnecting(false);
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  };

  // ============================================================================
  // 메시지 및 이벤트 처리
  // ============================================================================

  /**
   * 메시지 전송
   */
  const sendMessage = async (data: ChatRequest): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (!socketRef.current?.connected) {
        reject(new Error('Socket이 연결되지 않았습니다.'));
        return;
      }

      try {
        socketRef.current.emit('chat:send', data, (response: any) => {
          if (response?.error) {
            reject(new Error(response.error));
          } else {
            resolve();
          }
        });
      } catch (err) {
        reject(err);
      }
    });
  };

  /**
   * 세션 참여
   */
  const joinSession = (sessionId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('session:join', sessionId);
    }
  };

  /**
   * 세션 떠나기
   */
  const leaveSession = (sessionId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('session:leave', sessionId);
    }
  };

  // ============================================================================
  // 생명주기 관리
  // ============================================================================

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url, autoConnect]);

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  // ============================================================================
  // 반환값
  // ============================================================================

  return {
    socket: socketRef.current,
    isConnected,
    isConnecting,
    error,
    sendMessage,
    joinSession,
    leaveSession,
    connect,
    disconnect,
  };
};

// ============================================================================
// 유틸리티 훅들
// ============================================================================

/**
 * Socket 이벤트 리스너 훅
 */
export const useSocketEvent = <T = any>(
  socket: Socket | null,
  event: string,
  handler: (data: T) => void
) => {
  useEffect(() => {
    if (!socket) return;

    socket.on(event, handler);

    return () => {
      socket.off(event, handler);
    };
  }, [socket, event, handler]);
};

/**
 * 타이핑 상태 전송 훅
 */
export const useTypingIndicator = (socket: Socket | null, sessionId: string) => {
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const startTyping = () => {
    if (!socket?.connected || !sessionId) return;

    socket.emit('chat:typing:start', { sessionId });

    // 3초 후 자동으로 타이핑 중지
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      stopTyping();
    }, 3000);
  };

  const stopTyping = () => {
    if (!socket?.connected || !sessionId) return;

    socket.emit('chat:typing:stop', { sessionId });

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return { startTyping, stopTyping };
}; 