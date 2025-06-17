"""
🖥️ API SERVER (통합 FastAPI 서버)
===================================
역할: Chain과 연동되는 웹 API 서버

📖 새로운 구조에서의 역할:
- Chain과 1:1 연동으로 단순화된 아키텍처
- OpenAI 호환 API 제공 (/v1/chat/completions)
- 스트리밍 및 일반 응답 모두 지원
- MCP Config 기반 동적 도구 로딩

🔄 연동:
- ../agent/chain.py: 메인 체인 실행 엔진
- ../utils/llm_client.py: LLM 설정 통합
- MCP Config: 동적 MCP Server 연결

🚀 핵심 특징:
- 단순화된 아키텍처: Chain 하나만 관리
- 표준 호환: OpenAI API 호환성
- 유연한 설정: 환경변수 기반 구성
- 확장성: MCP Config를 통한 도구 확장
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from contextlib import asynccontextmanager

# FastAPI 관련
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# 상위 디렉토리 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.chain import Chain
from utils.llm_client import get_llm_client, get_llm_config, print_llm_status

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
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

# =============================================================================
# 🚀 FastAPI 애플리케이션 설정
# =============================================================================

# 글로벌 Chain 인스턴스
chain_instance: Optional[Chain] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global chain_instance
    
    # 시작 시 초기화
    logging.info("🚀 API 서버 초기화 시작")
    
    # LLM 설정 확인
    print_llm_status()
    
    # Chain 초기화
    llm_backend = os.environ.get("LLM_BACKEND", "openai")
    max_iterations = int(os.environ.get("MAX_ITERATIONS", "3"))
    
    try:
        chain_instance = Chain(llm_backend=llm_backend, max_iterations=max_iterations)
        logging.info(f"✅ Chain 초기화 완료: {llm_backend} 백엔드, 최대 {max_iterations}회 반복")
        
        # MCP 시스템 초기화 및 건강 상태 체크
        logging.info("🏥 MCP 시스템 초기화 중...")
        mcp_health = await chain_instance.initialize_mcp_system()
        
        if mcp_health.get('success'):
            logging.info(f"✅ MCP 시스템 준비완료: {mcp_health.get('available_tools', 0)}개 도구 사용가능")
        else:
            logging.warning(f"⚠️ MCP 시스템 부분실패: {mcp_health.get('error', '알 수 없는 오류')}")
            if mcp_health.get('fallback_needed'):
                logging.warning("🚨 폴백 모드로 실행됩니다 - 제한된 기능만 사용가능")
        
        # 권장사항 출력
        for recommendation in mcp_health.get('recommendations', []):
            logging.info(f"💡 {recommendation}")
            
    except Exception as e:
        logging.error(f"❌ Chain 초기화 실패: {e}")
        raise e
    
    yield
    
    # 종료 시 정리
    logging.info("🛑 API 서버 종료")

# FastAPI 앱 생성
app = FastAPI(
    title="MyAgent API Server",
    description="Plan-Execute-Reflect 체인 기반 데이터 분석 API",
    version="2.0.0",
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# 🎯 API 엔드포인트들
# =============================================================================

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "MyAgent API Server v2.0",
        "architecture": "Plan-Execute-Reflect Chain",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "status": "/status",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    global chain_instance
    
    if chain_instance is None:
        raise HTTPException(status_code=503, detail="Chain not initialized")
    
    # Chain 상태 확인
    try:
        chain_status = chain_instance.get_chain_status()
        llm_config = get_llm_config()
        
        # MCP 건강 상태 추가
        mcp_health = getattr(chain_instance, 'mcp_health_report', None)
        
        health_info = {
            "status": "healthy",
            "chain_ready": True,
            "llm_backend": llm_config["backend"],
            "chain_status": chain_status
        }
        
        # MCP 상태 정보 추가
        if mcp_health:
            health_info["mcp_status"] = {
                "initialized": chain_instance.mcp_initialized,
                "total_tools": mcp_health.get('total_tools', 0),
                "available_tools": mcp_health.get('available_tools', 0),
                "success_rate": mcp_health.get('overall_success_rate', 0.0),
                "fallback_needed": mcp_health.get('fallback_needed', False),
                "recommendations": mcp_health.get('recommendations', [])
            }
        else:
            health_info["mcp_status"] = {"initialized": False}
        
        return health_info
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "chain_ready": False,
            "mcp_status": {"initialized": False, "error": str(e)}
        }

@app.get("/status")
async def get_status():
    """서버 상태 조회"""
    global chain_instance
    
    if chain_instance is None:
        return {"error": "Chain not initialized"}
    
    try:
        return {
            "server_info": {
                "version": "2.0.0",
                "architecture": "Plan-Execute-Reflect",
                "backend": os.environ.get("LLM_BACKEND", "openai")
            },
            "chain_status": chain_instance.get_chain_status(),
            "llm_config": get_llm_config()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI 호환 채팅 완료 API
    
    Chain을 통해 Plan-Execute-Reflect 사이클 실행
    """
    global chain_instance
    
    if chain_instance is None:
        raise HTTPException(status_code=503, detail="Chain not initialized")
    
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
        
        # 스트리밍 응답 여부 확인
        if request.stream:
            return StreamingResponse(
                stream_chain_response(user_message, request),
                media_type="text/plain"
            )
        else:
            return await execute_chain_response(user_message, request)
    
    except Exception as e:
        logger.error(f"❌ 채팅 완료 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_chain_response(user_message: str, request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Chain 실행 및 일반 응답"""
    global chain_instance
    
    try:
        # Chain 실행
        result = chain_instance.run(user_message)
        
        # 응답 포맷팅
        if result.get('success'):
            # 성공 응답
            response_content = format_success_response(result)
        else:
            # 실패 응답
            response_content = f"❌ 분석 실패: {result.get('error', '알 수 없는 오류')}"
        
        # OpenAI 형식 응답 생성
        import time
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split())
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Chain 실행 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def stream_chain_response(user_message: str, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Chain 실행 및 스트리밍 응답"""
    global chain_instance
    
    try:
        import time
        import json
        
        # 스트리밍 시작 메시지
        yield f"data: {json.dumps({'content': '🚀 분석을 시작합니다...\\n'})}\n\n"
        await asyncio.sleep(0.1)
        
        # Chain 실행 (별도 스레드에서)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, chain_instance.run, user_message)
        
        # 진행 상황 스트리밍
        chain_summary = result.get('chain_summary', {})
        iterations = chain_summary.get('total_iterations', 1)
        
        yield f"data: {json.dumps({'content': f'📊 {iterations}회 반복 실행 완료\\n'})}\n\n"
        await asyncio.sleep(0.1)
        
        # 결과 포맷팅
        if result.get('success'):
            response_content = format_success_response(result)
        else:
            response_content = f"❌ 분석 실패: {result.get('error', '알 수 없는 오류')}"
        
        # 최종 결과 스트리밍
        yield f"data: {json.dumps({'content': response_content})}\n\n"
        
        # 스트리밍 종료
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"❌ 스트리밍 오류: {e}")
        yield f"data: {json.dumps({'content': f'❌ 오류: {str(e)}'})}\n\n"
        yield "data: [DONE]\n\n"

def format_success_response(result: Dict[str, Any]) -> str:
    """성공 응답 포맷팅"""
    try:
        question = result.get('question', '')
        chain_summary = result.get('chain_summary', {})
        primary_result = result.get('result', {})
        
        # 기본 정보
        response_parts = [
            f"✅ **질문**: {question}",
            f"🔄 **실행 방식**: {chain_summary.get('execution_strategy', 'Plan-Execute-Reflect')}",
            f"📊 **반복 횟수**: {chain_summary.get('total_iterations', 1)}회",
            f"⭐ **품질 점수**: {chain_summary.get('best_quality_score', 0):.2f}",
            ""
        ]
        
        # 결과 데이터
        result_format = result.get('result_format', 'unknown')
        
        if result_format == 'sql_query_result' and primary_result:
            # SQL 쿼리 결과
            response_parts.append("📈 **분석 결과**:")
            response_parts.append(f"- SQL 쿼리: `{primary_result.get('query_executed', 'N/A')}`")
            response_parts.append(f"- 결과 행 수: {primary_result.get('row_count', 0)}행")
            
            # 샘플 데이터 표시
            rows = primary_result.get('rows', [])
            if rows:
                response_parts.append("- 샘플 데이터:")
                for i, row in enumerate(rows[:3]):  # 최대 3행
                    response_parts.append(f"  {i+1}. {row}")
        
        elif result_format == 'table_info' and primary_result:
            # 테이블 정보
            response_parts.append("📋 **수집된 데이터**:")
            for table_name, table_info in primary_result.items():
                response_parts.append(f"- {table_name}: {table_info.get('row_count', 0)}행")
        
        # 차트 데이터
        chart_data = result.get('chart_data')
        if chart_data:
            chart_type = chart_data.get('type', 'unknown')
            response_parts.append(f"📊 **시각화**: {chart_type} 차트 생성됨")
        
        # 사용 가능한 데이터
        dataframes = result.get('available_dataframes', [])
        if dataframes:
            response_parts.append(f"💾 **로드된 데이터**: {', '.join(dataframes)}")
        
        return "\n".join(response_parts)
        
    except Exception as e:
        logger.error(f"❌ 응답 포맷팅 오류: {e}")
        return f"✅ 분석이 완료되었지만 결과 포맷팅 중 오류가 발생했습니다: {str(e)}"

# =============================================================================
# 🔧 추가 관리 엔드포인트들
# =============================================================================

@app.post("/reset")
async def reset_chain():
    """Chain 상태 초기화"""
    global chain_instance
    
    if chain_instance is None:
        raise HTTPException(status_code=503, detail="Chain not initialized")
    
    try:
        chain_instance.reset_chain()
        return {"message": "Chain 상태가 초기화되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/execution-summary")
async def get_execution_summary():
    """실행 요약 조회"""
    global chain_instance
    
    if chain_instance is None:
        raise HTTPException(status_code=503, detail="Chain not initialized")
    
    try:
        return chain_instance.get_execution_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/single-execution")
async def single_execution(request: Dict[str, str]):
    """단일 실행 (재계획 없이)"""
    global chain_instance
    
    if chain_instance is None:
        raise HTTPException(status_code=503, detail="Chain not initialized")
    
    question = request.get('question')
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        result = chain_instance.run_single_execution(question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# 🚀 메인 실행부
# =============================================================================

def main():
    """서버 실행"""
    # 환경변수 설정
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    
    logger.info(f"🚀 MyAgent API Server v2.0 시작")
    logger.info(f"📡 주소: http://{host}:{port}")
    logger.info(f"🤖 LLM 백엔드: {os.environ.get('LLM_BACKEND', 'openai')}")
    
    # 서버 실행
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main() 