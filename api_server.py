#!/usr/bin/env python3
"""
🚀 통합 AI Assistant API 서버 v3.0
====================================

📋 시스템 아키텍처:
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                          │
│                    http://localhost:3000                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP API Calls
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              통합 API 서버 (FastAPI)                           │
│                  http://localhost:8000                          │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                   │
│  │ Question        │    │ Smart Router    │                   │
│  │ Analyzer        │────▶│ - General Chat  │                   │
│  │                 │    │ - Data Analysis │                   │
│  └─────────────────┘    └─────────┬───────┘                   │
│                                   │                           │
│  ┌─────────────────┐              │   ┌─────────────────┐     │
│  │ OpenAI Client   │◀─────────────┼──▶│ MCP Client      │     │
│  │ (일반 대화)      │              │   │ (데이터 분석)    │     │
│  └─────────────────┘              │   └─────────┬───────┘     │
│                                   │             │             │
│  ┌─────────────────┐              │             │             │
│  │ Fallback System │◀─────────────┘             │             │
│  │ (MCP 연결실패시) │                             │             │
│  └─────────────────┘                             │             │
└───────────────────────────────────────────────────┼─────────────┘
                                                    │ stdio/JSON-RPC
                                                    ▼
                            ┌─────────────────────────────────────┐
                            │         KOSIS MCP Server            │
                            │     mcp_servers/kosis_server/       │
                            │                                     │
                            │  📊 Tools: 통계 데이터 조회          │
                            │  📁 Resources: 메타데이터           │
                            │  💬 Prompts: 분석 템플릿            │
                            └─────────────────┬───────────────────┘
                                              │ HTTPS API
                                              ▼
                                   ┌─────────────────────┐
                                   │   KOSIS Open API    │
                                   │   (통계청 공식 API)  │
                                   │   kosis.kr/openapi  │
                                   └─────────────────────┘

🎯 처리 플로우:
1. Frontend에서 사용자 질문 전송
2. Question Analyzer가 질문 유형 분석 (일반/데이터분석)
3. 일반 질문 → OpenAI API 직접 호출
4. 데이터 분석 → MCP Client를 통해 KOSIS 서버 연결
5. MCP 연결 실패시 → Fallback System으로 대체 응답
6. 스트리밍 또는 일반 응답으로 Frontend에 전달

🔧 주요 특징:
- OpenAI 호환 API 엔드포인트 (/v1/chat/completions)
- 스마트 라우팅으로 질문 유형에 따른 자동 처리
- MCP 표준 프로토콜 준수 (JSON-RPC 2.0)
- 견고한 Fallback 시스템
- 실시간 스트리밍 지원
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

# FastAPI 관련
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# OpenAI
import openai
from openai import OpenAI

# MCP Client (Optional)
try:
    from mcp_client.client import MCPClient, MCPServerConfig
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP client not available - using fallback mode")

# KOSIS Fallback
from kosis_fallback import analyze_data_question

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# 📋 REQUEST/RESPONSE 모델
# =============================================================================

class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "gpt-3.5-turbo"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

# =============================================================================
# 🧠 Question Analyzer
# =============================================================================

class QuestionAnalyzer:
    """질문 유형 분석기"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """질문 분석하여 처리 방식 결정"""
        
        # 데이터 관련 키워드
        data_keywords = [
            "통계", "데이터", "분석", "조회", "검색",
            "인구", "경제", "GDP", "물가", "고용",
            "KOSIS", "통계청", "자료", "수치",
            "얼마", "몇", "비교", "추이", "변화"
        ]
        
        # 일반 대화 패턴
        general_patterns = [
            "안녕", "감사", "고마워", "뭐야", "누구야",
            "시간", "날짜", "오늘", "내일", "어제",
            "도움", "설명", "알려줘", "뭘 할 수 있",
            "어떻게", "왜", "무엇", "누가", "언제"
        ]
        
        question_lower = question.lower()
        
        # 데이터 관련 질문 체크
        is_data_query = any(keyword in question_lower for keyword in data_keywords)
        
        # 명확한 일반 질문 체크
        is_general = any(pattern in question_lower for pattern in general_patterns)
        
        # 시간/날짜 관련 특별 처리
        if any(word in question_lower for word in ["몇시", "시간", "날짜", "오늘", "지금"]):
            return {
                "type": "general",
                "subtype": "datetime",
                "needs_mcp": False,
                "confidence": 0.95
            }
        
        # 최종 판단
        if is_data_query and not is_general:
            return {
                "type": "data_analysis",
                "needs_mcp": True,
                "confidence": 0.8
            }
        else:
            return {
                "type": "general",
                "needs_mcp": False,
                "confidence": 0.9
            }

# =============================================================================
# 🚀 FastAPI 애플리케이션
# =============================================================================

# 글로벌 인스턴스
mcp_client: Optional[MCPClient] = None
openai_client: Optional[OpenAI] = None
question_analyzer: Optional[QuestionAnalyzer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global mcp_client, openai_client, question_analyzer
    
    # 시작 시 초기화
    logging.info("🚀 통합 AI Assistant 서버 시작")
    
    # OpenAI 클라이언트 초기화
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    question_analyzer = QuestionAnalyzer(openai_client)
    logging.info("✅ OpenAI 클라이언트 초기화 완료")
    
    # MCP 클라이언트 초기화 (선택사항)
    if MCP_AVAILABLE:
        try:
            mcp_client = MCPClient()
            
            # KOSIS MCP 서버 추가 시도
            kosis_config = MCPServerConfig(
                name="kosis",
                command="python",
                args=["mcp_servers/kosis_server/server.py"],
                env={"KOSIS_OPEN_API_KEY": os.getenv("KOSIS_OPEN_API_KEY", "")}
            )
            
            try:
                connected = await mcp_client.add_server(kosis_config)
                if connected:
                    logging.info("✅ KOSIS MCP 서버 연결 성공")
                    
                    # 사용 가능한 도구 확인
                    tools = mcp_client.list_all_tools()
                    logging.info(f"📋 사용 가능한 도구: {len(tools)}개")
                    for tool in tools:
                        logging.info(f"  - {tool['name']}: {tool['description']}")
                else:
                    logging.warning("⚠️ KOSIS MCP 서버 연결 실패 - Fallback 모드로 동작")
            except Exception as e:
                logging.warning(f"⚠️ KOSIS MCP 서버 연결 오류: {e} - Fallback 모드로 동작")
                
        except Exception as e:
            logging.warning(f"⚠️ MCP 클라이언트 초기화 실패: {e} - Fallback 모드로 동작")
            mcp_client = None
    else:
        logging.info("📋 MCP 패키지 없음 - Fallback 모드로 동작")
        mcp_client = None
    
    yield
    
    # 종료 시 정리
    if mcp_client:
        await mcp_client.close_all()
    logging.info("🛑 서버 종료")

# FastAPI 앱 생성
app = FastAPI(
    title="통합 AI Assistant API",
    description="General 대화와 데이터 분석을 모두 지원하는 AI Assistant",
    version="3.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP 관련 로그 레벨 조정
logging.getLogger("MCPClient").setLevel(logging.WARNING)

# =============================================================================
# 🎯 메인 엔드포인트
# =============================================================================

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "통합 AI Assistant API v3.0",
        "capabilities": ["general_chat", "data_analysis", "kosis_integration"],
        "endpoints": {
            "chat": "/v1/chat/completions",
            "health": "/health",
            "tools": "/tools"
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    global mcp_client, openai_client
    
    health_status = {
        "status": "healthy",
        "openai": openai_client is not None,
        "mcp_servers": []
    }
    
    if mcp_client:
        servers = mcp_client.list_servers()
        health_status["mcp_servers"] = servers
        
    return health_status

@app.get("/tools")
async def list_tools():
    """사용 가능한 도구 목록"""
    global mcp_client
    
    if not mcp_client:
        return {"tools": [], "message": "MCP client not initialized"}
        
    return {
        "tools": mcp_client.list_all_tools(),
        "resources": mcp_client.list_all_resources(),
        "prompts": mcp_client.list_all_prompts()
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI 호환 채팅 API"""
    global mcp_client, openai_client, question_analyzer
    
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not initialized")
    
    try:
        # 사용자 메시지 추출
        user_message = None
        for message in request.messages:
            if message.role == "user":
                user_message = message.content
                break
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")
        
        logger.info(f"📨 사용자 질문: {user_message}")
        
        # 질문 분석
        analysis = question_analyzer.analyze_question(user_message)
        logger.info(f"📊 질문 분석: {analysis}")
        
        # 처리 방식에 따라 라우팅
        if analysis["type"] == "general":
            # 일반 대화는 OpenAI 직접 사용
            return await handle_general_chat(request, user_message, analysis)
        else:
            # 데이터 분석은 MCP 도구 사용
            return await handle_data_analysis(request, user_message)
            
    except Exception as e:
        logger.error(f"❌ 채팅 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_general_chat(request: ChatCompletionRequest, user_message: str, analysis: Dict[str, Any]):
    """일반 대화 처리"""
    global openai_client
    
    # 시스템 프롬프트 설정
    system_prompt = """당신은 친절하고 도움이 되는 AI 어시스턴트입니다.
    
사용자의 질문에 자연스럽고 대화체로 답변하세요.
한국어로 답변하며, 이모지를 적절히 사용하여 친근감을 표현하세요.

주의사항:
- 데이터나 통계 관련 질문이 아닌 일반 대화에 집중하세요
- 시간이나 날짜를 물으면 현재 시각 기준으로 답변하세요
- 모르는 것은 솔직히 모른다고 답변하세요"""
    
    # 날짜/시간 특별 처리
    if analysis.get("subtype") == "datetime":
        current_time = datetime.now()
        time_context = f"\n\n현재 시각: {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}"
        system_prompt += time_context
    
    # 메시지 구성
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # OpenAI API 호출
    if request.stream:
        return StreamingResponse(
            stream_openai_response(messages, request),
            media_type="text/event-stream"
        )
    else:
        response = openai_client.chat.completions.create(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return {
            "id": f"chatcmpl-{datetime.now().timestamp():.0f}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.choices[0].message.content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

async def handle_data_analysis(request: ChatCompletionRequest, user_message: str):
    """데이터 분석 질문 처리"""
    global mcp_client, openai_client
    
    # MCP 서버 연결 상태 확인
    mcp_available = False
    if mcp_client:
        servers = mcp_client.list_servers()
        mcp_available = any(server.get("connected", False) for server in servers)
    
    logger.info(f"🔌 MCP 서버 연결 상태: {mcp_available}")
    
    # MCP가 사용 가능한 경우와 불가능한 경우 다른 프롬프트 사용
    if mcp_available:
        system_prompt = """당신은 한국 통계청(KOSIS) 데이터 분석 전문가입니다.

사용 가능한 도구:
1. search_kosis: KOSIS 데이터 검색
2. fetch_kosis_data: 특정 통계표 데이터 조회
3. get_stat_list: 통계 목록 조회

사용자의 질문을 분석하여 적절한 도구를 사용하고, 
데이터를 기반으로 정확하고 통찰력 있는 답변을 제공하세요."""
    else:
        system_prompt = """당신은 데이터 분석 전문가입니다.

현재 KOSIS 데이터베이스에 직접 연결할 수 없지만, 
한국 통계청 데이터에 대한 일반적인 정보와 분석 방법을 제공할 수 있습니다.

다음과 같은 정보를 포함하여 답변하세요:
1. 해당 주제의 일반적인 통계 현황
2. 데이터 수집 방법과 출처
3. 분석 시 고려해야 할 요소들
4. 트렌드 및 인사이트

답변 마지막에 "실시간 데이터는 KOSIS(kosis.kr)에서 확인하실 수 있습니다."를 추가하세요."""
    
    try:
        if mcp_available:
            # MCP 서버가 연결된 경우 도구 호출 시도
            plan_messages = [
                {"role": "system", "content": """당신은 데이터 분석 계획을 수립하는 AI입니다. 
사용자 질문에 답하기 위해 어떤 KOSIS 도구를 어떻게 사용할지 JSON 형식으로 계획을 세우세요.

응답 형식:
{
  "steps": [
    {
      "tool": "search_kosis|fetch_kosis_data|get_stat_list",
      "params": {...},
      "purpose": "이 단계의 목적"
    }
  ],
  "explanation": "전체 계획 설명"
}"""},
                {"role": "user", "content": f"{user_message}\n\n위 질문에 답하기 위한 도구 사용 계획을 JSON으로 작성하세요."}
            ]
            
            plan_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=plan_messages,
                max_tokens=500,
                temperature=0.1
            )
            
            # 계획 JSON 파싱
            plan_text = plan_response.choices[0].message.content
            plan_json = json.loads(plan_text) if plan_text.startswith('{') else {"steps": [], "explanation": "계획 수립 실패"}
            
            # MCP 도구 실행
            results = []
            for step in plan_json.get("steps", []):
                tool_name = step.get("tool")
                params = step.get("params", {})
                
                if tool_name and tool_name in ["search_kosis", "fetch_kosis_data", "get_stat_list"]:
                    try:
                        # MCP 도구 호출
                        result = await mcp_client.call_tool("kosis", tool_name, params)
                        results.append({
                            "tool": tool_name,
                            "success": result.get("success", False),
                            "content": result.get("content", {})
                        })
                    except Exception as e:
                        logger.error(f"MCP tool call failed: {e}")
                        results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": str(e)
                        })
            
            # 결과 기반 응답 생성
            analysis_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": f"데이터 수집 결과:\n{json.dumps(results, ensure_ascii=False, indent=2)}"},
                {"role": "user", "content": "위 데이터를 기반으로 사용자 질문에 대한 분석 결과를 작성해주세요."}
            ]
            
            final_response = openai_client.chat.completions.create(
                model=request.model,
                messages=analysis_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            response_content = final_response.choices[0].message.content
        else:
            # MCP 서버가 연결되지 않은 경우 Fallback 모드 사용
            logger.info("📋 MCP 서버 미연결로 Fallback 데이터 분석 사용")
            
            # Fallback 데이터 조회
            fallback_data = analyze_data_question(user_message)
            
            # 데이터를 포함한 컨텍스트로 답변 생성
            context_message = f"""
사용자 질문: {user_message}

조회된 데이터:
{json.dumps(fallback_data, ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 사용자의 질문에 대해 상세하고 유용한 분석 답변을 제공하세요.
"""
            
            analysis_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_message}
            ]
            
            final_response = openai_client.chat.completions.create(
                model=request.model,
                messages=analysis_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            response_content = final_response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Data analysis error: {e}")
        response_content = f"""
📊 데이터 분석 중 오류가 발생했습니다.

질문: {user_message}
오류: {str(e)}

대신 일반적인 정보를 제공해드릴게요.
KOSIS(통계청)에서는 인구, 경제, 사회 등 다양한 통계 데이터를 제공합니다.
구체적인 데이터 조회를 원하시면 다시 시도해주세요.
"""
    
    if request.stream:
        return StreamingResponse(
            stream_simple_response(response_content),
            media_type="text/event-stream"
        )
    else:
        return {
            "id": f"chatcmpl-{datetime.now().timestamp():.0f}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }]
        }

# =============================================================================
# 🌊 스트리밍 헬퍼
# =============================================================================

async def stream_openai_response(messages: List[Dict[str, str]], request: ChatCompletionRequest):
    """OpenAI 스트리밍 응답"""
    global openai_client
    
    stream = openai_client.chat.completions.create(
        model=request.model,
        messages=messages,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
    
    yield "data: [DONE]\n\n"

async def stream_simple_response(content: str):
    """간단한 스트리밍 응답"""
    # 문장 단위로 분할하여 스트리밍
    sentences = content.split('\n')
    for sentence in sentences:
        if sentence.strip():
            yield f"data: {json.dumps({'content': sentence + '\\n'})}\n\n"
            await asyncio.sleep(0.1)
    
    yield "data: [DONE]\n\n"

# =============================================================================
# 🚀 메인 실행부
# =============================================================================

def main():
    """서버 실행"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"🚀 통합 AI Assistant 서버 시작")
    logger.info(f"📡 주소: http://{host}:{port}")
    logger.info(f"🔑 OpenAI API: {'설정됨' if os.getenv('OPENAI_API_KEY') else '미설정'}")
    logger.info(f"📊 KOSIS API: {'설정됨' if os.getenv('KOSIS_OPEN_API_KEY') else '미설정'}")
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 