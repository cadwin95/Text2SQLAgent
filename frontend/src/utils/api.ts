// utils/api.ts
// ============
// 통합 AI Assistant API 통신 유틸리티
// - 스마트 라우팅 (일반 대화 + 데이터 분석)
// - OpenAI 호환 API 연동
// - 스트리밍 응답 처리

import axios from 'axios';
import { ChatRequest, ChatResponse } from '@/types';

// API 클라이언트 설정
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 60000, // 60초 타임아웃 (데이터 분석 고려)
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    console.log('🚀 API 요청:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('❌ API 요청 오류:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => {
    console.log('✅ API 응답:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('❌ API 응답 오류:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

/**
 * 질문 유형 분석 (클라이언트 사이드 미리 감지)
 */
const analyzeQuestionType = (message: string): 'general' | 'data_analysis' => {
  const dataKeywords = [
    '통계', '데이터', '분석', '조회', '검색',
    '인구', '경제', 'GDP', '물가', '고용',
    'KOSIS', '통계청', '자료', '수치',
    '얼마', '몇', '비교', '추이', '변화'
  ];
  
  const lowerMessage = message.toLowerCase();
  const hasDataKeywords = dataKeywords.some(keyword => 
    lowerMessage.includes(keyword.toLowerCase())
  );
  
  return hasDataKeywords ? 'data_analysis' : 'general';
};

/**
 * 채팅 메시지 전송
 */
export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  try {
    const questionType = analyzeQuestionType(request.message);
    
    // OpenAI 호환 요청 형식
    const openAIRequest = {
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "user",
          content: request.message
        }
      ],
      max_tokens: 1000,
      temperature: 0.7,
      stream: false
    };

    console.log(`🧠 질문 유형: ${questionType === 'general' ? '일반 대화' : '데이터 분석'}`);

    const response = await apiClient.post('/v1/chat/completions', openAIRequest);
    
    // OpenAI 호환 응답 파싱
    const content = response.data.choices[0]?.message?.content || "응답을 생성할 수 없습니다.";
    
    // 응답에서 차트 데이터나 테이블 데이터 추출
    let chartData = null;
    let tableData = null;
    
    // 테이블 데이터 파싱 (Markdown 테이블 또는 JSON 형식)
    const tableMatch = content.match(/```(?:json)?\n(.*?)\n```/s);
    if (tableMatch) {
      try {
        const tableText = tableMatch[1];
        
        // JSON 형식 시도
        try {
          const jsonData = JSON.parse(tableText);
          if (jsonData.columns && jsonData.rows) {
            tableData = jsonData;
          }
        } catch {
          // Markdown 테이블 형식 파싱
          const lines = tableText.split('\n').filter((line: string) => line.trim());
          if (lines.length > 2) {
            const headers = lines[0].split('|').map((h: string) => h.trim()).filter((h: string) => h);
            const rows = lines.slice(2).map((line: string) => 
              line.split('|').map((cell: string) => cell.trim()).filter((cell: string) => cell)
            );
            
            if (headers.length > 0 && rows.length > 0) {
              tableData = {
                columns: headers,
                rows: rows
              };
            }
          }
        }
      } catch (parseError) {
        console.warn('⚠️ 테이블 데이터 파싱 실패:', parseError);
      }
    }
    
    // 차트 데이터 추출 (JSON 형식)
    const chartMatch = content.match(/\[CHART_DATA\](.*?)\[\/CHART_DATA\]/s);
    if (chartMatch) {
      try {
        chartData = JSON.parse(chartMatch[1]);
      } catch (parseError) {
        console.warn('⚠️ 차트 데이터 파싱 실패:', parseError);
      }
    }
    
    return {
      message: {
        id: `msg-${Date.now()}`,
        content: content,
        role: 'assistant',
        timestamp: new Date(),
        metadata: {
          queryType: questionType === 'data_analysis' ? 'analysis' : 'text2sql',
          dataSource: questionType === 'data_analysis' ? 'kosis' : 'openai',
          executionTime: Date.now() % 1000,
          chartData: chartData,
          tableData: tableData
        }
      },
      sessionId: request.sessionId || 'default',
      suggestions: questionType === 'data_analysis' ? [
        "한국의 최근 인구 통계를 보여주세요",
        "GDP 성장률 추이를 분석해주세요",
        "시도별 경제지표를 비교해주세요"
      ] : [
        "다른 질문이 있으신가요?",
        "더 자세한 설명이 필요하신가요?",
        "관련된 다른 주제도 물어보세요"
      ]
    };
  } catch (error) {
    console.error('❌ 채팅 메시지 전송 실패:', error);
    
    // 오류 응답 생성
    return {
      message: {
        id: `error-${Date.now()}`,
        content: getErrorMessage(error),
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
    const questionType = analyzeQuestionType(request.message);
    console.log(`🧠 스트리밍 질문 유형: ${questionType === 'general' ? '일반 대화' : '데이터 분석'}`);
    
    // OpenAI 호환 스트리밍 요청
    const openAIRequest = {
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "user",
          content: request.message
        }
      ],
      max_tokens: 1000,
      temperature: 0.7,
      stream: true
    };

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/v1/chat/completions`, {
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
    let fullContent = '';

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
            const dataStr = line.slice(6).trim(); // 'data: ' 제거
            
            if (dataStr === '[DONE]') {
              // 스트리밍 완료
              onUpdate({
                type: 'complete',
                content: fullContent,
                questionType: questionType,
                status: 'completed'
              });
              return;
            }
            
            try {
              const data = JSON.parse(dataStr);
              if (data.content) {
                fullContent += data.content;
                onUpdate({
                  type: 'content',
                  content: data.content,
                  fullContent: fullContent,
                  questionType: questionType,
                  status: 'streaming'
                });
              }
            } catch (parseError) {
              console.warn('⚠️ 스트리밍 JSON 파싱 오류:', parseError, dataStr);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

  } catch (error) {
    console.error('❌ 스트리밍 채팅 메시지 전송 실패:', error);
    onUpdate({
      type: 'error',
      message: getErrorMessage(error),
      status: 'error'
    });
  }
};

/**
 * 서버 상태 확인
 */
export const checkServerHealth = async (): Promise<{
  status: boolean;
  openai: boolean;
  mcp_servers: any[];
}> => {
  try {
    const response = await apiClient.get('/health');
    return {
      status: response.status === 200,
      openai: response.data.openai || false,
      mcp_servers: response.data.mcp_servers || []
    };
  } catch (error) {
    console.error('❌ 서버 상태 확인 실패:', error);
    return {
      status: false,
      openai: false,
      mcp_servers: []
    };
  }
};

/**
 * MCP 도구 목록 조회
 */
export const getMCPTools = async (): Promise<{
  tools: any[];
  resources: any[];
  prompts: any[];
}> => {
  try {
    const response = await apiClient.get('/tools');
    return {
      tools: response.data.tools || [],
      resources: response.data.resources || [],
      prompts: response.data.prompts || []
    };
  } catch (error) {
    console.error('❌ MCP 도구 목록 조회 실패:', error);
    return {
      tools: [],
      resources: [],
      prompts: []
    };
  }
};

/**
 * 오류 메시지 생성
 */
const getErrorMessage = (error: any): string => {
  if (error.response) {
    const status = error.response.status;
    const message = error.response.data?.detail || error.response.data?.message || '서버 오류가 발생했습니다.';
    
    switch (status) {
      case 400:
        return `잘못된 요청입니다: ${message}`;
      case 401:
        return 'API 키 인증이 필요합니다. 환경변수를 확인해주세요.';
      case 403:
        return 'API 접근이 거부되었습니다.';
      case 404:
        return '요청한 엔드포인트를 찾을 수 없습니다.';
      case 429:
        return '너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.';
      case 500:
        return `서버 내부 오류: ${message}`;
      case 503:
        return '서비스를 사용할 수 없습니다. OpenAI 또는 MCP 서버 연결을 확인해주세요.';
      default:
        return `서버 오류 (${status}): ${message}`;
    }
  } else if (error.request) {
    return '서버에 연결할 수 없습니다. 네트워크 연결과 서버 상태를 확인해주세요.';
  } else {
    return `요청 처리 중 오류가 발생했습니다: ${error.message}`;
  }
};

/**
 * API 오류 처리 유틸리티 (하위 호환성)
 */
export const handleApiError = (error: any): string => {
  return getErrorMessage(error);
}; 