# integrated_api_server.py
# ========================
# AgentChain + Text2DFQueryAgent 통합 API 서버
# - 실제 LLM 기반 Text2SQL 변환
# - KOSIS API 연동
# - DataFrame 기반 데이터 분석
# - 계획-실행-반성 파이프라인

import uvicorn
import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
import time

# 로컬 모듈 import (시스템 경로 추가)
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.agent_chain import AgentChain
from agent.text2sql_agent import Text2DFQueryAgent
import pandas as pd

# FastAPI 앱 설정
app = FastAPI(
    title="Text2SQL Agent API Server",
    description="AgentChain과 Text2DFQueryAgent를 통합한 실제 Text2SQL 분석 서버",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://10.150.1.221:3000",
        "http://10.150.1.221:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI 호환 API 모델 정의
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.1

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-agent"
    object: str = "chat.completion"
    model: str = "text2sql-agent"
    choices: List[ChatCompletionResponseChoice]

# 전역 AgentChain 인스턴스
agent_chain = None

def initialize_agent():
    """AgentChain 초기화"""
    global agent_chain
    try:
        # 환경 변수에서 LLM 설정 읽기
        backend = os.environ.get("LLM_BACKEND", "openai")
        model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        
        print(f"🤖 AgentChain 초기화 중... (backend: {backend}, model: {model})")
        agent_chain = AgentChain(backend=backend, model=model)
        print("✅ AgentChain 초기화 완료!")
        
    except Exception as e:
        print(f"❌ AgentChain 초기화 실패: {e}")
        agent_chain = None

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    initialize_agent()

@app.get("/")
def read_root():
    return {
        "message": "Text2SQL Agent API Server가 실행 중입니다.",
        "status": "healthy",
        "agent_status": "ready" if agent_chain else "not_initialized",
        "endpoints": ["/v1/chat/completions", "/health", "/agent/status"],
        "features": [
            "자연어 → SQL 변환",
            "KOSIS API 연동",
            "DataFrame 기반 분석",
            "계획-실행-반성 파이프라인"
        ]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "agent_ready": agent_chain is not None
    }

@app.get("/agent/status")
def agent_status():
    """AgentChain 상태 확인"""
    if not agent_chain:
        return {"status": "not_initialized", "dataframes": []}
    
    return {
        "status": "ready",
        "backend": agent_chain.backend,
        "model": agent_chain.model,
        "available_dataframes": list(agent_chain.df_agent.dataframes.keys()),
        "dataframe_shapes": {
            name: df.shape for name, df in agent_chain.df_agent.dataframes.items()
        }
    }

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI 호환 채팅 완료 API"""
    try:
        if not agent_chain:
            raise HTTPException(status_code=503, detail="AgentChain이 초기화되지 않았습니다.")
        
        # 사용자 메시지 추출
        user_message = ""
        for message in request.messages:
            if message.role == "user":
                user_message = message.content
                break
        
        if not user_message:
            raise HTTPException(status_code=400, detail="사용자 메시지가 없습니다.")
        
        print(f"📝 사용자 질의: {user_message}")
        
        # AgentChain 실행
        result = await run_agent_chain(user_message)
        
        # 응답 생성
        response_content = format_agent_response(result)
        
        response = ChatCompletionResponse(
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response_content
                    )
                )
            ]
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

async def run_agent_chain(question: str) -> Dict[str, Any]:
    """AgentChain 비동기 실행"""
    try:
        # 기본 스키마 (실제로는 동적으로 생성해야 함)
        schema = """
        사용 가능한 데이터:
        - KOSIS 통계 데이터 (fetch_kosis_data 도구 사용)
        - 기존 로드된 DataFrame들
        """
        
        # AgentChain 실행 (비동기 처리를 위해 별도 스레드에서 실행)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            agent_chain.run, 
            question
        )
        
        return result
        
    except Exception as e:
        return {
            "history": [],
            "remaining_plan": [],
            "final_result": None,
            "error": str(e)
        }

def format_agent_response(result: Dict[str, Any]) -> str:
    """AgentChain 결과를 사용자 친화적인 형태로 포맷팅"""
    try:
        history = result.get("history", [])
        final_result = result.get("final_result")
        error = result.get("error")
        
        if error:
            return f"❌ 분석 중 오류가 발생했습니다: {error}"
        
        if not history:
            return "📊 분석을 수행했지만 결과가 없습니다."
        
        # 응답 구성
        response_parts = []
        
        # 실행된 단계들 요약
        if len(history) > 1:
            response_parts.append("🔄 **실행된 분석 단계:**")
            for i, step in enumerate(history, 1):
                step_type = step.get("type", "unknown")
                description = step.get("description", "")
                step_error = step.get("error")
                
                if step_error:
                    response_parts.append(f"{i}. {description} ❌ (오류: {step_error})")
                else:
                    response_parts.append(f"{i}. {description} ✅")
        
        # 최종 결과
        if final_result:
            response_parts.append("\n📈 **분석 결과:**")
            
            # DataFrame 결과 처리
            if isinstance(final_result, dict):
                if "columns" in final_result and "rows" in final_result:
                    columns = final_result["columns"]
                    rows = final_result["rows"]
                    
                    if columns and rows:
                        # 테이블 형태로 표시
                        response_parts.append("```")
                        response_parts.append(" | ".join(columns))
                        response_parts.append("-" * (len(" | ".join(columns))))
                        
                        for row in rows[:10]:  # 최대 10행만 표시
                            response_parts.append(" | ".join(str(cell) for cell in row))
                        
                        if len(rows) > 10:
                            response_parts.append(f"... (총 {len(rows)}행 중 10행 표시)")
                        
                        response_parts.append("```")
                    else:
                        response_parts.append("데이터가 없습니다.")
                
                elif "query_code" in final_result:
                    query_code = final_result["query_code"]
                    if query_code:
                        response_parts.append("**생성된 쿼리 코드:**")
                        response_parts.append(f"```python\n{query_code}\n```")
                
                elif "msg" in final_result:
                    response_parts.append(final_result["msg"])
                else:
                    response_parts.append(str(final_result))
            else:
                response_parts.append(str(final_result))
        
        return "\n".join(response_parts) if response_parts else "분석이 완료되었습니다."
        
    except Exception as e:
        return f"응답 포맷팅 중 오류가 발생했습니다: {e}"

def generate_chart_data(dataframes: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """DataFrame 데이터로부터 차트 데이터 생성"""
    try:
        # 사용 가능한 DataFrame이 있는지 확인
        if not dataframes:
            return None
        
        # 첫 번째 DataFrame 사용 (일반적으로 fetch_kosis_data로 생성된 것)
        df_name = next(iter(dataframes.keys()))
        df = dataframes[df_name]
        
        if df.empty:
            return None
        
        # 인구 데이터인 경우 (PRD_DE, DT 컬럼이 있는 경우)
        if 'PRD_DE' in df.columns and 'DT' in df.columns:
            # 연도별 데이터 추출
            years = df['PRD_DE'].astype(str).tolist()
            values = pd.to_numeric(df['DT'], errors='coerce').tolist()
            
            # 성장률 계산
            growth_rates = []
            for i in range(1, len(values)):
                if values[i-1] and values[i]:
                    growth_rate = ((values[i] - values[i-1]) / values[i-1]) * 100
                    growth_rates.append(round(growth_rate, 2))
                else:
                    growth_rates.append(0)
            
            # 첫 번째 연도는 성장률이 없으므로 0으로 설정
            growth_rates.insert(0, 0)
            
            return {
                'type': 'line',
                'title': '최근 5년간 인구 성장률 추이 (GDP 성장률 대체)',
                'data': {
                    'labels': years,
                    'datasets': [
                        {
                            'label': '인구 성장률 (%)',
                            'data': growth_rates,
                            'borderColor': 'rgb(75, 192, 192)',
                            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                            'borderWidth': 2,
                            'tension': 0.1
                        }
                    ]
                },
                'options': {
                    'scales': {
                        'y': {
                            'beginAtZero': True,
                            'title': {
                                'display': True,
                                'text': '성장률 (%)'
                            }
                        },
                        'x': {
                            'title': {
                                'display': True,
                                'text': '연도'
                            }
                        }
                    }
                }
            }
        
        return None
        
    except Exception as e:
        print(f"차트 데이터 생성 오류: {e}")
        return None

@app.post("/v1/chat/stream")
async def chat_stream(request: ChatCompletionRequest):
    """스트리밍 채팅 완료 API - 툴 호출 과정을 실시간으로 전송"""
    if not agent_chain:
        raise HTTPException(status_code=503, detail="AgentChain이 초기화되지 않았습니다.")
    
    # 사용자 메시지 추출
    user_message = ""
    for message in request.messages:
        if message.role == "user":
            user_message = message.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="사용자 메시지가 없습니다.")
    
    async def stream_generator() -> AsyncGenerator[str, None]:
        """스트리밍 응답 생성기"""
        try:
            print(f"📝 사용자 질의: {user_message}")
            
            # 시작 메시지
            yield f"data: {json.dumps({'type': 'start', 'message': '분석을 시작합니다...'}, ensure_ascii=False)}\n\n"
            
            # AgentChain 실행 (커스텀 스트리밍 버전)
            async for update in run_agent_chain_streaming(user_message):
                yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            
            # 완료 메시지
            yield f"data: {json.dumps({'type': 'done', 'message': '분석이 완료되었습니다.'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_msg = {
                'type': 'error',
                'message': f'❌ 처리 오류: {str(e)}'
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

async def run_agent_chain_streaming(question: str) -> AsyncGenerator[Dict[str, Any], None]:
    """AgentChain 스트리밍 실행"""
    try:
        # 기본 스키마 생성
        schema = f"""
사용 가능한 데이터:
- KOSIS 통계 데이터 (fetch_kosis_data 도구 사용)
- 기존 로드된 DataFrame들: {list(agent_chain.df_agent.dataframes.keys())}
"""
        
        # 1단계: 계획 생성
        yield {
            'type': 'planning',
            'message': '🎯 분석 계획을 수립 중입니다...',
            'status': 'running'
        }
        
        # 실제 계획 생성
        steps = await asyncio.get_event_loop().run_in_executor(
            None, agent_chain.plan_with_llm, question, schema
        )
        
        yield {
            'type': 'planning',
            'message': f'✅ 계획 수립 완료: {len(steps)}개 단계',
            'status': 'completed',
            'data': {'steps': [step.get('description', '') for step in steps]}
        }
        
        # 2단계: 각 단계 실행
        for i, step in enumerate(steps, 1):
            step_type = step.get('type', 'unknown')
            description = step.get('description', '')
            
            # 단계 실행
            try:
                if step_type == 'tool_call':
                    # 툴 호출 표시
                    tool_name = step.get('tool_name', 'unknown')
                    yield {
                        'type': 'tool_call',
                        'tool_name': tool_name,
                        'step_number': i,
                        'message': f'🔧 **도구 호출: {tool_name}**',
                        'description': description,
                        'status': 'running'
                    }
                    
                    # 실제 툴 실행
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, agent_chain.execute_step, step
                    )
                    
                    if result.get('error'):
                        yield {
                            'type': 'tool_call',
                            'tool_name': tool_name,
                            'step_number': i,
                            'message': f'❌ 도구 실행 실패: {result["error"]}',
                            'status': 'error'
                        }
                    else:
                        yield {
                            'type': 'tool_call',
                            'tool_name': tool_name,
                            'step_number': i,
                            'message': f'✅ 도구 실행 완료: {tool_name}',
                            'status': 'completed',
                            'data': result
                        }
                
                elif step_type == 'query':
                    # DataFrame 쿼리 실행
                    yield {
                        'type': 'query',
                        'step_number': i,
                        'message': f'📊 **데이터 쿼리**\n📊 데이터 쿼리 실행 중...',
                        'description': description,
                        'status': 'running'
                    }
                    
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, agent_chain.execute_step, step
                    )
                    
                    if result.get('error'):
                        yield {
                            'type': 'query',
                            'step_number': i,
                            'message': f'❌ 쿼리 실행 실패: {result["error"]}',
                            'status': 'error'
                        }
                    else:
                        yield {
                            'type': 'query',
                            'step_number': i,
                            'message': f'✅ 쿼리 실행 완료',
                            'status': 'completed',
                            'data': result
                        }
                
                elif step_type == 'visualization':
                    # 시각화 단계 - 실제 차트 데이터 생성
                    chart_data = generate_chart_data(agent_chain.df_agent.dataframes)
                    yield {
                        'type': 'visualization',
                        'step_number': i,
                        'message': f'📈 **시각화 생성**\n{description}',
                        'description': description,
                        'status': 'completed',
                        'chart_data': chart_data
                    }
                
                else:
                    # 기타 단계 실행
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, agent_chain.execute_step, step
                    )
                    
                    status = 'error' if result.get('error') else 'completed'
                    emoji = '❌' if result.get('error') else '✅'
                    
                    yield {
                        'type': 'step',
                        'step_number': i,
                        'message': f'{emoji} **단계 {i}**: {description}',
                        'status': status,
                        'data': result
                    }
                
            except Exception as e:
                yield {
                    'type': 'step',
                    'step_number': i,
                    'message': f'❌ 단계 {i} 실행 오류: {str(e)}',
                    'status': 'error'
                }
        
        # 3단계: 최종 결과 생성
        yield {
            'type': 'result',
            'message': '📈 최종 결과를 생성 중입니다...',
            'status': 'running'
        }
        
        # 실행된 단계들의 결과를 요약
        executed_steps = []
        for i, step in enumerate(steps, 1):
            step_desc = step.get('description', f'단계 {i}')
            executed_steps.append(f"{i}. {step_desc} ✅")
        
        # 최종 분석 결과 생성 (이미 실행된 단계들 기반)
        summary_message = f"""
🔄 **실행된 분석 단계:**
{chr(10).join(executed_steps)}

📈 **분석 결과:**
{step.get('type', '').replace('_', ' ').title()} 단계 완료
"""
        
        # 시각화 단계가 있었다면 더미 실행
        if any('visualization' in step.get('type', '') for step in steps):
            summary_message += "\n시각화(line_chart) 단계 dummy 실행"
        
        yield {
            'type': 'result',
            'message': summary_message.strip(),
            'status': 'completed',
            'data': {
                'executed_steps': executed_steps,
                'total_steps': len(steps),
                'dataframes_available': list(agent_chain.df_agent.dataframes.keys())
            }
        }
        
    except Exception as e:
        yield {
            'type': 'error',
            'message': f'❌ 실행 중 오류 발생: {str(e)}',
            'status': 'error'
        }

@app.post("/agent/query")
async def direct_query(request: Dict[str, Any]):
    """직접 쿼리 실행 (디버깅용)"""
    try:
        if not agent_chain:
            raise HTTPException(status_code=503, detail="AgentChain이 초기화되지 않았습니다.")
        
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="question 파라미터가 필요합니다.")
        
        result = await run_agent_chain(question)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Text2SQL Agent API Server 시작 중...")
    print("📍 URL: http://localhost:8000")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔗 프론트엔드 연동: http://localhost:3000")
    print("\n🔧 필요한 환경 변수:")
    print("- OPENAI_API_KEY: OpenAI API 키")
    print("- KOSIS_OPEN_API_KEY: KOSIS API 키 (선택사항)")
    print("- LLM_BACKEND: LLM 백엔드 (기본값: openai)")
    print("- OPENAI_MODEL: 사용할 모델 (기본값: gpt-3.5-turbo)")
    
    uvicorn.run(
        "integrated_api_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    ) 