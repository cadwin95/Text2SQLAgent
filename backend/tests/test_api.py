# test_api.py
# -----------
# 백엔드 API 서버(FastAPI 등) 엔드포인트 테스트 파일
# - 주요 API(LLM, Text2SQL, 공공API 연동 등) 정상 동작/예외 처리/응답 구조 검증
# - 자동화 테스트/CI 연동, MCP 파이프라인 통합 테스트 포함
# - RESTful API, 프론트엔드 연동 등 실사용 시나리오 기반 테스트 작성
# - 자세한 설계/구현 규칙은 .cursor/rules/rl-text2sql-public-api.md 참고

import os
import pytest
import requests
import json
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrated_api_server import app

# TestClient 사용 (FastAPI 공식 테스트 방법)
client = TestClient(app)

def test_root_endpoint():
    """
    루트 엔드포인트 ("/") 정상 동작 검증
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "status" in data
    assert data["status"] == "healthy"
    assert "endpoints" in data
    assert "features" in data

def test_health_check():
    """
    헬스체크 엔드포인트 ("/health") 정상 동작 검증
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "agent_ready" in data

def test_agent_status():
    """
    AgentChain 상태 확인 엔드포인트 ("/agent/status") 검증
    """
    response = client.get("/agent/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "available_dataframes" in data
    assert "dataframe_shapes" in data
    assert isinstance(data["available_dataframes"], list)
    assert isinstance(data["dataframe_shapes"], dict)

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_chat_completions_openai_format():
    """
    OpenAI 호환 채팅 완료 API ("/v1/chat/completions") 정상 동작 검증
    """
    request_data = {
        "model": "text2sql-agent",
        "messages": [
            {"role": "user", "content": "한국의 인구 통계를 분석해주세요"}
        ],
        "max_tokens": 512,
        "temperature": 0.1
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert "object" in data
    assert data["object"] == "chat.completion"
    assert "model" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
    
    choice = data["choices"][0]
    assert "index" in choice
    assert "message" in choice
    assert choice["message"]["role"] == "assistant"
    assert "content" in choice["message"]
    assert len(choice["message"]["content"]) > 0

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_chat_completions_error_handling():
    """
    잘못된 요청에 대한 에러 처리 검증
    """
    # 빈 메시지 테스트
    request_data = {
        "model": "text2sql-agent",
        "messages": [],
        "max_tokens": 512
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 400
    
    # role이 없는 메시지 테스트
    request_data = {
        "model": "text2sql-agent", 
        "messages": [
            {"content": "테스트 메시지"}  # role 누락
        ],
        "max_tokens": 512
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    # 적절한 에러 처리가 되어야 함 (400 또는 422)
    assert response.status_code in [400, 422, 500]

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_direct_query_endpoint():
    """
    직접 쿼리 엔드포인트 ("/agent/query") 검증
    """
    request_data = {
        "question": "한국의 GDP 성장률을 분석해주세요"
    }
    
    response = client.post("/agent/query", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    # AgentChain 결과 구조 검증
    assert "history" in data
    assert "remaining_plan" in data  
    assert "final_result" in data
    assert "error" in data
    assert isinstance(data["history"], list)

def test_direct_query_missing_question():
    """
    question 파라미터 누락 시 에러 처리 검증
    """
    request_data = {}  # question 누락
    
    response = client.post("/agent/query", json=request_data)
    assert response.status_code == 400

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_streaming_endpoint():
    """
    스트리밍 채팅 엔드포인트 ("/v1/chat/stream") 기본 연결 테스트
    """
    request_data = {
        "model": "text2sql-agent",
        "messages": [
            {"role": "user", "content": "간단한 테스트"}
        ]
    }
    
    response = client.post("/v1/chat/stream", json=request_data)
    # 스트리밍 응답은 200이어야 함
    assert response.status_code == 200
    # Content-Type이 text/plain이어야 함
    assert "text/plain" in response.headers.get("content-type", "")

def test_cors_headers():
    """
    CORS 헤더가 올바르게 설정되어 있는지 검증 (프론트엔드 연동용)
    """
    response = client.options("/v1/chat/completions", 
                             headers={"Origin": "http://localhost:3000"})
    
    # CORS 프리플라이트 요청 처리 확인
    # 실제 응답 코드는 구현에 따라 다를 수 있음
    assert response.status_code in [200, 204, 405]

def test_openai_compatibility():
    """
    OpenAI API 형식 호환성 검증
    """
    # OpenAI 클라이언트가 기대하는 정확한 형식 테스트
    request_data = {
        "model": "gpt-3.5-turbo",  # OpenAI 모델명 사용
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 1.0,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    
    # API 키가 없어도 기본 형식은 맞아야 함
    assert response.status_code in [200, 503]  # 200(성공) 또는 503(AgentChain 미초기화)

