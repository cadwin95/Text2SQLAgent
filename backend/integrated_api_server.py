# integrated_api_server.py
# ========================
# 🖥️ MCP CLIENT (Model Context Protocol Client)
# ========================
# 역할: LLM 기반 Text2SQL 분석 서비스를 제공하는 MCP 클라이언트 서버
# 
# 📖 MCP 아키텍처에서의 위치:
# - MCP Client: 이 파일이 LLM과 MCP Server 사이의 중재자 역할
# - MCP Server: mcp_api_v2.py가 KOSIS API 도구들을 제공
# - Frontend: React/Next.js 프론트엔드가 이 서버와 통신
#
# 🎯 주요 기능:
# 1. FastAPI 기반 웹 API 서버 제공
# 2. LLM 기반 자연어 → SQL 변환
# 3. MCP Server의 도구들을 활용한 데이터 수집
# 4. AgentChain을 통한 계획-실행-반성 파이프라인
# 5. 스트리밍 응답으로 실시간 진행 상황 전송
#
# 🔄 데이터 흐름:
# Frontend → MCP Client(이 파일) → LLM → MCP Server(mcp_api_v2.py) → KOSIS API
#
# 🚀 MCP 분리 구조의 장점:
# 1. **관심사 분리**: 
#    - Client는 비즈니스 로직과 API 서버 담당
#    - Server는 외부 API 연동과 도구 제공 담당
# 2. **확장성**: 
#    - 새로운 API 추가 시 MCP Server만 수정
#    - 다른 MCP Server들도 쉽게 연결 가능
# 3. **유지보수성**: 
#    - API 변경사항이 Client 로직에 영향 없음
#    - 독립적인 테스트와 배포 가능
# 4. **재사용성**: 
#    - MCP Server는 다른 프로젝트에서도 재사용 가능
#    - 표준 MCP 프로토콜 준수로 호환성 확보
# 5. **성능**: 
#    - MCP Server는 캐싱과 최적화에 집중
#    - Client는 사용자 경험에 집중
#
# 참고: https://modelcontextprotocol.io/introduction
# MCP 분리 패턴: https://python.plainenglish.io/build-your-own-mcp-server-in-an-hour-a8a1d80b54b5

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
import numpy as np

# 로컬 모듈 import (시스템 경로 추가)
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 핵심 에이전트 모듈들
from agent.agent_chain import AgentChain
from agent.text2sql_agent import Text2DFQueryAgent
import pandas as pd

# FastAPI 앱 설정 - MCP Client 서버
app = FastAPI(
    title="Text2SQL MCP Client API Server",
    description="MCP Client: LLM 기반 Text2SQL 분석과 MCP Server 연동을 제공하는 통합 서버",
    version="2.0.0"
)

# CORS 설정 - 프론트엔드 연동
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

# 🤖 전역 AgentChain 인스턴스 (MCP Client의 핵심 컴포넌트)
agent_chain = None

def initialize_agent():
    """
    MCP Client의 핵심 에이전트 초기화
    - AgentChain: 계획-실행-반성 파이프라인 관리
    - MCP Server 연동: mcp_api_v2.py의 도구들을 활용
    """
    global agent_chain
    try:
        # 환경 변수에서 LLM 설정 읽기
        backend = os.environ.get("LLM_BACKEND", "openai")
        model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        
        print(f"🤖 MCP Client AgentChain 초기화 중... (backend: {backend}, model: {model})")
        agent_chain = AgentChain(backend=backend, model=model)
        print("✅ MCP Client AgentChain 초기화 완료!")
        print("🔗 MCP Server 연동 준비 완료 (mcp_api_v2.py)")
        
    except Exception as e:
        print(f"❌ MCP Client AgentChain 초기화 실패: {e}")
        agent_chain = None

@app.on_event("startup")
async def startup_event():
    """MCP Client 서버 시작 시 초기화"""
    initialize_agent()

@app.get("/")
def read_root():
    return {
        "message": "Text2SQL MCP Client API Server가 실행 중입니다.",
        "status": "healthy",
        "agent_status": "ready" if agent_chain else "not_initialized",
        "mcp_architecture": {
            "client": "integrated_api_server.py (이 서버)",
            "server": "mcp_api_v2.py (KOSIS API 도구 제공)",
            "external_service": "KOSIS OpenAPI"
        },
        "endpoints": ["/v1/chat/completions", "/v1/chat/stream", "/health", "/agent/status"],
        "features": [
            "MCP 기반 자연어 → SQL 변환",
            "KOSIS API 자동 연동",
            "DataFrame 기반 분석",
            "실시간 스트리밍 응답",
            "계획-실행-반성 파이프라인"
        ]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "mcp_client_ready": agent_chain is not None,
        "mcp_server_status": "external (mcp_api_v2.py)"
    }

@app.get("/agent/status")
def agent_status():
    """MCP Client AgentChain 상태 확인"""
    if not agent_chain:
        return {"status": "not_initialized", "dataframes": []}
    
    return {
        "status": "ready",
        "backend": agent_chain.backend,
        "model": agent_chain.model,
        "mcp_client_info": {
            "available_dataframes": list(agent_chain.df_agent.dataframes.keys()),
            "dataframe_shapes": {
                name: df.shape for name, df in agent_chain.df_agent.dataframes.items()
            },
            "mcp_server_tools": [
                "fetch_kosis_data", "get_stat_list", "get_stat_explanation",
                "get_table_meta", "get_bigdata", "search_kosis"
            ]
        }
    }

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI 호환 채팅 완료 API - MCP Client 엔드포인트"""
    try:
        if not agent_chain:
            raise HTTPException(status_code=503, detail="MCP Client AgentChain이 초기화되지 않았습니다.")
        
        # 사용자 메시지 추출
        user_message = ""
        for message in request.messages:
            if message.role == "user":
                user_message = message.content
                break
        
        if not user_message:
            raise HTTPException(status_code=400, detail="사용자 메시지가 없습니다.")
        
        print(f"📝 [MCP Client] 사용자 질의: {user_message}")
        
        # MCP Client → AgentChain → MCP Server 파이프라인 실행
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
        print(f"❌ [MCP Client] 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP Client 서버 오류: {str(e)}")

async def run_agent_chain(question: str) -> Dict[str, Any]:
    """
    MCP Client AgentChain 비동기 실행
    - LLM을 통한 계획 수립
    - MCP Server 도구들을 활용한 데이터 수집
    - DataFrame 기반 분석 실행
    """
    try:
        # 기본 스키마 (MCP Server 도구들 정보 포함)
        schema = f"""
MCP 아키텍처 기반 사용 가능한 데이터 소스:
- KOSIS 통계 데이터 (MCP Server의 fetch_kosis_data 도구 사용)
- 기존 로드된 DataFrame들: {list(agent_chain.df_agent.dataframes.keys())}

MCP Server 제공 도구들:
- fetch_kosis_data: 통계자료 직접 조회
- get_stat_list: 통계목록 탐색
- search_kosis: 키워드 검색
- get_table_meta: 메타데이터 조회
"""
        
        # AgentChain 실행 (MCP Server와 연동)
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
    """MCP Client AgentChain 결과를 사용자 친화적인 형태로 포맷팅"""
    try:
        history = result.get("history", [])
        final_result = result.get("final_result")
        error = result.get("error")
        
        if error:
            return f"❌ MCP Client 분석 중 오류가 발생했습니다: {error}"
        
        if not history:
            return "📊 MCP 기반 분석을 수행했지만 결과가 없습니다."
        
        # 응답 구성
        response_parts = []
        
        # 실행된 단계들 요약 (MCP Server 도구 호출 포함)
        if len(history) > 1:
            response_parts.append("🔄 **MCP 기반 실행된 분석 단계:**")
            for i, step in enumerate(history, 1):
                step_type = step.get("type", "unknown")
                description = step.get("description", "")
                step_error = step.get("error")
                
                # MCP Server 도구 호출 표시
                if step_type == "tool_call":
                    emoji = "🔧"
                elif step_type == "query":
                    emoji = "📊"
                else:
                    emoji = "⚙️"
                
                if step_error:
                    response_parts.append(f"{i}. {emoji} {description} ❌ (오류: {step_error})")
                else:
                    response_parts.append(f"{i}. {emoji} {description} ✅")
        
        # 최종 결과
        if final_result:
            response_parts.append("\n📈 **MCP 분석 결과:**")
            
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
                        response_parts.append("MCP Server에서 데이터를 가져왔지만 내용이 없습니다.")
                
                elif "query_code" in final_result:
                    query_code = final_result["query_code"]
                    if query_code:
                        response_parts.append("**생성된 SQL 쿼리 코드:**")
                        response_parts.append(f"```sql\n{query_code}\n```")
                
                elif "msg" in final_result:
                    response_parts.append(final_result["msg"])
                else:
                    response_parts.append(str(final_result))
            else:
                response_parts.append(str(final_result))
        
        return "\n".join(response_parts) if response_parts else "MCP 기반 분석이 완료되었습니다."
        
    except Exception as e:
        return f"MCP Client 응답 포맷팅 중 오류가 발생했습니다: {e}"

def generate_chart_data(dataframes: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """MCP Server에서 수집한 DataFrame 데이터로부터 차트 데이터 생성"""
    try:
        # 사용 가능한 DataFrame이 있는지 확인
        if not dataframes:
            print("[MCP Client 차트 생성] DataFrame이 없습니다")
            return None
        
        # 첫 번째 DataFrame 사용 (일반적으로 MCP Server의 fetch_kosis_data로 생성된 것)
        df_name = next(iter(dataframes.keys()))
        df = dataframes[df_name]
        
        print(f"[MCP Client 차트 생성] DataFrame: {df_name}, 컬럼: {df.columns.tolist()}, 행 수: {len(df)}")
        
        if df.empty:
            print("[MCP Client 차트 생성] MCP Server에서 가져온 DataFrame이 비어있습니다")
            return None
        
        # KOSIS 데이터인 경우 (PRD_DE, DT 컬럼이 있는 경우)
        if 'PRD_DE' in df.columns and 'DT' in df.columns:
            # 실제 MCP Server API 데이터 그대로 사용
            years = df['PRD_DE'].astype(str).tolist()
            values = pd.to_numeric(df['DT'], errors='coerce').fillna(0).tolist()
            
            print(f"[MCP Client 차트 생성] 실제 KOSIS API 데이터 - 연도: {years}, 값: {values}")
            
            # 실제 데이터 값을 그대로 표시 (성장률이 아닌 원본 수치)
            chart_data = {
                'type': 'line',
                'title': 'MCP Server에서 가져온 실제 KOSIS 데이터',
                'data': {
                    'labels': years,
                    'datasets': [
                        {
                            'label': '실제 수치값',
                            'data': values,
                            'borderColor': 'rgb(54, 162, 235)',
                            'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                            'borderWidth': 2,
                            'tension': 0.1,
                            'fill': False
                        }
                    ]
                },
                'options': {
                    'responsive': True,
                    'scales': {
                        'y': {
                            'beginAtZero': false,
                            'title': {
                                'display': True,
                                'text': '값'
                            }
                        },
                        'x': {
                            'title': {
                                'display': True,
                                'text': '연도'
                            }
                        }
                    },
                    'plugins': {
                        'legend': {
                            'display': true
                        }
                    }
                }
            }
            
            print(f"[MCP Client 차트 생성 성공] KOSIS 데이터: {chart_data}")
            return chart_data
        
        # 다른 데이터 타입들도 지원 - 실제 API 데이터 그대로 표시
        # 숫자 컬럼이 있는 경우 - 바 차트로 실제 데이터 표시
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_columns) >= 1:
            # 첫 번째 컬럼을 레이블로, 첫 번째 숫자 컬럼을 값으로 사용
            if len(df.columns) >= 2:
                labels = df.iloc[:, 0].astype(str).tolist()  
                values = pd.to_numeric(df[numeric_columns[0]], errors='coerce').fillna(0).tolist()
                value_column = numeric_columns[0]
            else:
                # 컬럼이 하나뿐인 경우 인덱스를 레이블로 사용
                labels = [f"항목 {i+1}" for i in range(len(df))]
                values = pd.to_numeric(df[numeric_columns[0]], errors='coerce').fillna(0).tolist()
                value_column = numeric_columns[0]
            
            chart_data = {
                'type': 'bar',
                'title': f'MCP Server 실제 데이터: {value_column}',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': f'실제 {value_column} 값',
                            'data': values,
                            'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                            'borderColor': 'rgba(75, 192, 192, 1)',
                            'borderWidth': 1
                        }
                    ]
                },
                'options': {
                    'responsive': True,
                    'scales': {
                        'y': {
                            'beginAtZero': false,
                            'title': {
                                'display': True,
                                'text': value_column
                            }
                        }
                    }
                }
            }
            
            print(f"[MCP Client 차트 생성 성공] 일반 바 차트: {chart_data}")
            return chart_data
        
        print("[MCP Client 차트 생성] 적합한 데이터 구조를 찾을 수 없습니다")
        return None
        
    except Exception as e:
        print(f"MCP Client 차트 데이터 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.post("/v1/chat/stream")
async def chat_stream(request: ChatCompletionRequest):
    """
    스트리밍 채팅 완료 API - MCP Client의 실시간 응답
    MCP Server 도구 호출 과정을 실시간으로 전송
    """
    if not agent_chain:
        raise HTTPException(status_code=503, detail="MCP Client AgentChain이 초기화되지 않았습니다.")
    
    # 사용자 메시지 추출
    user_message = ""
    for message in request.messages:
        if message.role == "user":
            user_message = message.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="사용자 메시지가 없습니다.")
    
    async def stream_generator() -> AsyncGenerator[str, None]:
        """MCP Client 스트리밍 응답 생성기"""
        try:
            print(f"📝 [MCP Client Stream] 사용자 질의: {user_message}")
            
            # 시작 메시지
            yield f"data: {json.dumps({'type': 'start', 'message': 'MCP 기반 분석을 시작합니다...'}, ensure_ascii=False)}\n\n"
            
            # MCP Client AgentChain 실행 (MCP Server와 연동하는 스트리밍 버전)
            async for update in run_agent_chain_streaming(user_message):
                yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            
            # 완료 메시지
            yield f"data: {json.dumps({'type': 'done', 'message': 'MCP 기반 분석이 완료되었습니다.'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_msg = {
                'type': 'error',
                'message': f'❌ MCP Client 처리 오류: {str(e)}'
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
    """
    MCP Client AgentChain 스트리밍 실행
    MCP Server 도구 호출 과정을 실시간으로 보고
    """
    try:
        # MCP Server 도구 정보를 포함한 스키마 생성
        schema = f"""
MCP 아키텍처 기반 사용 가능한 데이터:
- KOSIS 통계 데이터 (MCP Server의 fetch_kosis_data 도구 사용)
- 기존 로드된 DataFrame들: {list(agent_chain.df_agent.dataframes.keys())}

MCP Server 연동 상태: mcp_api_v2.py
"""
        
        # 1단계: 계획 생성
        yield {
            'type': 'planning',
            'message': '🎯 MCP 기반 분석 계획을 수립 중입니다...',
            'status': 'running'
        }
        
        # 실제 계획 생성 (MCP Server 도구들을 고려)
        steps = await asyncio.get_event_loop().run_in_executor(
            None, agent_chain.plan_with_llm, question, schema
        )
        
        yield {
            'type': 'planning',
            'message': f'✅ MCP 계획 수립 완료: {len(steps)}개 단계',
            'status': 'completed',
            'data': {'steps': [step.get('description', '') for step in steps]}
        }
        
        # 2단계: 각 단계 실행 (MCP Server 도구 호출 포함)
        for i, step in enumerate(steps, 1):
            step_type = step.get('type', 'unknown')
            description = step.get('description', '')
            
            # 단계 실행
            try:
                if step_type == 'tool_call':
                    # MCP Server 도구 호출 표시
                    tool_name = step.get('tool_name', 'unknown')
                    yield {
                        'type': 'tool_call',
                        'tool_name': tool_name,
                        'step_number': i,
                        'message': f'🔧 **MCP Server 도구 호출: {tool_name}**',
                        'description': description,
                        'status': 'running'
                    }
                    
                    # 실제 MCP Server 도구 실행
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, agent_chain.execute_step, step
                    )
                    
                    if result.get('error'):
                        yield {
                            'type': 'tool_call',
                            'tool_name': tool_name,
                            'step_number': i,
                            'message': f'❌ MCP Server 도구 실행 실패: {result["error"]}',
                            'status': 'error'
                        }
                    else:
                        yield {
                            'type': 'tool_call',
                            'tool_name': tool_name,
                            'step_number': i,
                            'message': f'✅ MCP Server 도구 실행 완료: {tool_name}',
                            'status': 'completed',
                            'data': result
                        }
                
                elif step_type == 'query':
                    # SQL 기반 DataFrame 쿼리 실행
                    yield {
                        'type': 'query',
                        'step_number': i,
                        'message': f'📊 **MCP Client 데이터 쿼리**\n🔄 질문을 SQL 쿼리로 변환 중...',
                        'description': description,
                        'status': 'running'
                    }
                    
                    try:
                        # SQL 기반 처리를 위한 Text2DFQueryAgent 사용
                        from agent.text2sql_agent import Text2DFQueryAgent
                        sql_agent = Text2DFQueryAgent()
                        
                        # 기존 DataFrame들을 SQL 테이블로 등록 (MCP Server에서 가져온 데이터 포함)
                        registered_tables = []
                        for df_name, df in agent_chain.df_agent.dataframes.items():
                            table_name = sql_agent.register_dataframe(df_name, df)
                            if table_name:
                                registered_tables.append(table_name)
                        
                        if registered_tables:
                            yield {
                                'type': 'query',
                                'step_number': i,
                                'message': f'🗃️ MCP 데이터 SQL 테이블 등록 완료: {", ".join(registered_tables)}',
                                'status': 'running'
                            }
                            
                            # SQL 쿼리 생성 및 실행
                            sql_result = sql_agent.run(question)
                            
                            if sql_result.get("error"):
                                yield {
                                    'type': 'query',
                                    'step_number': i,
                                    'message': f'❌ SQL 쿼리 실행 실패: {sql_result["error"]}',
                                    'status': 'error'
                                }
                            else:
                                sql_query = sql_result.get("sql_query")
                                sql_data = sql_result.get("result")
                                
                                # SQL 쿼리 표시
                                if sql_query:
                                    yield {
                                        'type': 'query',
                                        'step_number': i,
                                        'message': f'🔍 **생성된 SQL 쿼리:**\n```sql\n{sql_query}\n```',
                                        'status': 'running'
                                    }
                                
                                # 결과 데이터 처리
                                table_data = None
                                if sql_data and sql_data.get("rows"):
                                    table_data = {
                                        'columns': sql_data.get("columns", []),
                                        'rows': sql_data.get("rows", [])[:10],  # 최대 10행만 표시
                                        'total_rows': len(sql_data.get("rows", [])),
                                        'sql_query': sql_query
                                    }
                                
                                yield {
                                    'type': 'query',
                                    'step_number': i,
                                    'message': f'✅ MCP 데이터 SQL 쿼리 실행 완료 - {len(sql_data.get("rows", []))}행 결과',
                                    'status': 'completed',
                                    'data': sql_result,
                                    'table_data': table_data
                                }
                        else:
                            # Fallback: 기존 pandas 방식
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
                                # 쿼리 결과에서 테이블 데이터 추출
                                query_result = result.get('result', {})
                                table_data = None
                                
                                if isinstance(query_result, dict) and 'columns' in query_result and 'rows' in query_result:
                                    table_data = {
                                        'columns': query_result['columns'],
                                        'rows': query_result['rows'][:10],  # 최대 10행만 표시
                                        'total_rows': len(query_result['rows']),
                                        'query_code': query_result.get('query_code', '')
                                    }
                                
                                yield {
                                    'type': 'query',
                                    'step_number': i,
                                    'message': f'✅ 쿼리 실행 완료 (pandas)',
                                    'status': 'completed',
                                    'data': result,
                                    'table_data': table_data
                                }
                    
                    except Exception as e:
                        yield {
                            'type': 'query',
                            'step_number': i,
                            'message': f'❌ 쿼리 처리 중 오류: {str(e)}',
                            'status': 'error'
                        }
                
                elif step_type == 'visualization':
                    # 시각화 단계 - MCP Server에서 가져온 데이터로 차트 생성
                    chart_data = generate_chart_data(agent_chain.df_agent.dataframes)
                    yield {
                        'type': 'visualization',
                        'step_number': i,
                        'message': f'📈 **MCP 데이터 시각화 생성**\n{description}',
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
                        'message': f'{emoji} **MCP 단계 {i}**: {description}',
                        'status': status,
                        'data': result
                    }
                
            except Exception as e:
                yield {
                    'type': 'step',
                    'step_number': i,
                    'message': f'❌ MCP 단계 {i} 실행 오류: {str(e)}',
                    'status': 'error'
                }
        
        # 3단계: 최종 결과 생성
        available_dataframes = list(agent_chain.df_agent.dataframes.keys())
        if available_dataframes:
            result_message = f"✅ MCP 기반 분석이 완료되었습니다. {len(available_dataframes)}개의 데이터셋을 로드했습니다: {', '.join(available_dataframes)}"
        else:
            result_message = "✅ MCP 기반 분석이 완료되었습니다."
        
        yield {
            'type': 'result',
            'message': result_message,
            'status': 'completed',
            'data': {
                'total_steps': len(steps),
                'dataframes_available': available_dataframes,
                'mcp_server_tools_used': [step.get('tool_name') for step in steps if step.get('type') == 'tool_call']
            }
        }
        
    except Exception as e:
        yield {
            'type': 'error',
            'message': f'❌ MCP Client 실행 중 오류 발생: {str(e)}',
            'status': 'error'
        }

@app.post("/agent/query")
async def direct_query(request: Dict[str, Any]):
    """직접 쿼리 실행 (MCP Client 디버깅용)"""
    try:
        if not agent_chain:
            raise HTTPException(status_code=503, detail="MCP Client AgentChain이 초기화되지 않았습니다.")
        
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
    print("🚀 Text2SQL MCP Client API Server 시작 중...")
    print("🏗️ MCP 아키텍처:")
    print("   📡 MCP Client: integrated_api_server.py (이 서버)")
    print("   🔧 MCP Server: mcp_api_v2.py (KOSIS API 도구 제공)")
    print("   🌐 External Service: KOSIS OpenAPI")
    print("📍 URL: http://localhost:8000")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔗 프론트엔드 연동: http://localhost:3000")
    print("\n🔧 필요한 환경 변수:")
    print("- OPENAI_API_KEY: OpenAI API 키")
    print("- KOSIS_OPEN_API_KEY: KOSIS API 키 (MCP Server용)")
    print("- LLM_BACKEND: LLM 백엔드 (기본값: openai)")
    print("- OPENAI_MODEL: 사용할 모델 (기본값: gpt-3.5-turbo)")
    print("\n💡 MCP 분리 구조의 장점:")
    print("- 관심사 분리: Client(비즈니스로직) ↔ Server(API연동)")
    print("- 확장성: 새로운 API는 MCP Server만 수정")
    print("- 유지보수성: 독립적인 테스트와 배포")
    print("- 재사용성: 표준 MCP 프로토콜 준수")
    
    uvicorn.run(
        "integrated_api_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    ) 