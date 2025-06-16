// utils/api.ts
// ============
// 백엔드 API 통신 유틸리티
// - HTTP 클라이언트 설정
// - API 요청/응답 처리
// - 오류 처리

import axios from 'axios';
import { ChatRequest, ChatResponse } from '@/types';

// API 클라이언트 설정
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000, // 30초 타임아웃
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    console.log('API 요청:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('API 요청 오류:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => {
    console.log('API 응답:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('API 응답 오류:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

/**
 * 채팅 메시지 전송
 */
export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  try {
    // OpenAI 호환 API 형식으로 변환
    const openAIRequest = {
      model: "text2sql",
      messages: [
        {
          role: "user",
          content: request.message
        }
      ],
      max_tokens: 512,
      temperature: 0.1
    };

    const response = await apiClient.post('/v1/chat/completions', openAIRequest);
    
    // OpenAI 응답을 ChatResponse 형식으로 변환
    const sqlQuery = response.data.choices[0]?.message?.content || "SELECT 1;";
    
    return {
      message: {
        id: `msg-${Date.now()}`,
        content: `SQL 쿼리가 생성되었습니다:\n\`\`\`sql\n${sqlQuery}\n\`\`\``,
        role: 'assistant',
        timestamp: new Date(),
        metadata: {
          queryType: 'text2sql',
          dataSource: 'generated',
          executionTime: Date.now() % 1000, // 임시 실행 시간
        }
      },
      sessionId: request.sessionId || 'default',
      suggestions: [
        "한국의 인구 통계를 보여주세요",
        "서울시 부동산 가격 동향을 분석해주세요",
        "최근 5년간 GDP 성장률을 비교해주세요"
      ]
    };
  } catch (error) {
    console.error('채팅 메시지 전송 실패:', error);
    
    // 오류 응답 생성
    return {
      message: {
        id: `error-${Date.now()}`,
        content: '죄송합니다. 현재 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.',
        role: 'assistant',
        timestamp: new Date(),
        error: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.',
      },
      sessionId: request.sessionId || 'default',
    };
  }
};

/**
 * 스트리밍 채팅 메시지 전송
 */
export const sendChatMessageStream = async (
  request: ChatRequest,
  onUpdate: (update: any) => void
): Promise<void> => {
  try {
    // OpenAI 호환 API 형식으로 변환
    const openAIRequest = {
      model: "text2sql",
      messages: [
        {
          role: "user",
          content: request.message
        }
      ],
      max_tokens: 512,
      temperature: 0.1
    };

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(openAIRequest),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('스트림 리더를 생성할 수 없습니다.');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        // 청크를 문자열로 디코딩하고 버퍼에 추가
        buffer += decoder.decode(value, { stream: true });

        // 완전한 메시지들을 추출
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 마지막 불완전한 라인은 버퍼에 보관

        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)); // 'data: ' 제거
              onUpdate(data);
            } catch (parseError) {
              console.warn('JSON 파싱 오류:', parseError, line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

  } catch (error) {
    console.error('스트리밍 채팅 메시지 전송 실패:', error);
    onUpdate({
      type: 'error',
      message: error instanceof Error ? error.message : '스트리밍 연결 오류가 발생했습니다.',
      status: 'error'
    });
  }
};

/**
 * 서버 상태 확인
 */
export const checkServerHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/');
    return response.status === 200;
  } catch (error) {
    console.error('서버 상태 확인 실패:', error);
    return false;
  }
};

/**
 * API 오류 처리 유틸리티
 */
export const handleApiError = (error: any): string => {
  if (error.response) {
    // 서버가 응답했지만 오류 상태 코드
    const status = error.response.status;
    const message = error.response.data?.message || error.response.data?.error || '서버 오류가 발생했습니다.';
    
    switch (status) {
      case 400:
        return `잘못된 요청: ${message}`;
      case 401:
        return '인증이 필요합니다.';
      case 403:
        return '접근이 거부되었습니다.';
      case 404:
        return '요청한 리소스를 찾을 수 없습니다.';
      case 429:
        return '너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.';
      case 500:
        return '서버 내부 오류가 발생했습니다.';
      default:
        return `서버 오류 (${status}): ${message}`;
    }
  } else if (error.request) {
    // 요청이 전송되었지만 응답을 받지 못함
    return '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.';
  } else {
    // 요청 설정 중 오류 발생
    return `요청 오류: ${error.message}`;
  }
}; 