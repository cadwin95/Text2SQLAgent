# agent_chain.py
# ==============
# 🤖 AGENT CHAIN: MCP 기반 계획-실행-반성 파이프라인
# ==============
# 역할: MCP Client의 핵심 컴포넌트로서 LLM 기반 분석 워크플로우 관리
#
# 📖 MCP 아키텍처에서의 위치:
# - MCP Client Component: integrated_api_server.py의 핵심 에이전트
# - MCP Server 연동: mcp_api_v2.py의 도구들을 LLM을 통해 호출
# - 워크플로우 관리: Plan → Execute → Reflect → Replan 사이클
#
# 🎯 주요 기능:
# 1. LLM 기반 분석 계획 수립 (MCP Server 도구들을 고려)
# 2. MCP Server 도구 호출을 통한 데이터 수집
# 3. DataFrame 기반 SQL 쿼리 실행 및 분석
# 4. 실패 시 자동 재계획 및 대안 전략 수립
# 5. Text2DFQueryAgent와 연동한 SQL 변환
#
# 🔄 MCP 워크플로우:
# 1. LLM이 질문 분석 → MCP Server 도구 호출 계획 수립
# 2. MCP Server 도구 실행 → KOSIS API에서 데이터 수집
# 3. 수집된 데이터를 DataFrame으로 변환 → SQL 테이블 등록
# 4. LLM이 SQL 쿼리 생성 → Text2DFQueryAgent로 실행
# 5. 결과 분석 및 시각화 → 필요 시 재계획
#
# 🚀 통합된 에이전트 아키텍처:
# - AgentChain: 전체 워크플로우 조율
# - Text2DFQueryAgent: SQL 쿼리 실행 전담
# - MCP Server Tools: 외부 데이터 수집 전담
# - LLM Client: 자연어 이해 및 코드 생성
#
# 🛠️ 지원하는 LLM 백엔드:
# - OpenAI API, HuggingFace, GGUF 등 다양한 백엔드
# - 환경변수를 통한 동적 백엔드 선택
#
# 참고: MCP 프로토콜 - https://modelcontextprotocol.io/introduction
# 자세한 설계 규칙: .cursor/rules/rl-text2sql-public-api.md

import os
import sys
import json
import pandas as pd

# 상대 import를 절대 import로 변경
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.text2sql_agent import Text2DFQueryAgent
from llm_client import get_llm_client

# MCP Server API 클라이언트 사용 (FastMCP 기반)
try:
    from mcp_api_v2 import fetch_kosis_data, get_stat_list, convert_to_dataframe
    print("[AgentChain] ✅ FastMCP 기반 KOSIS MCP Server 연동")
except ImportError:
    # 백업용 기존 API (호환성 유지)
    from mcp_api import fetch_kosis_data, get_stat_list
    convert_to_dataframe = lambda x: pd.DataFrame(x.get("data", []))
    print("[AgentChain] ⚠️ 레거시 KOSIS API 사용 (MCP Server 미사용)")

# MCP Server 도구 명세 (검증된 도구만 포함)
MCP_TOOL_SPECS = [
    {
        "tool_name": "fetch_kosis_data",
        "description": "KOSIS 통계자료 직접 조회 (MCP Server 주요 도구)",
        "params": ["orgId", "tblId", "prdSe", "startPrdDe", "endPrdDe", "itmId", "objL1"],
        "mcp_server": "mcp_api_v2.py",
        "external_api": "KOSIS OpenAPI",
        "examples": [
            {
                "description": "2020-2024 전국 인구수 조회",
                "params": {"orgId": "101", "tblId": "DT_1B040A3", "prdSe": "Y", "startPrdDe": "2020", "endPrdDe": "2024", "itmId": "T20", "objL1": "00"}
            },
            {
                "description": "최근 5년 인구 통계",
                "params": {"orgId": "101", "tblId": "DT_1B040A3", "prdSe": "Y", "itmId": "T20", "objL1": "00"}
            }
        ]
    },
    {
        "tool_name": "get_stat_list", 
        "description": "KOSIS 통계목록 탐색 (MCP Server 메타데이터 도구)",
        "params": ["vwCd", "parentListId", "format"],
        "mcp_server": "mcp_api_v2.py",
        "external_api": "KOSIS OpenAPI"
    }
]

MCP_TOOL_SPEC_STR = json.dumps({"mcp_server_tools": MCP_TOOL_SPECS}, ensure_ascii=False)

class AgentChain:
    """
    🤖 AgentChain: MCP 기반 LLM 에이전트의 핵심 워크플로우 관리자
    
    MCP 아키텍처에서의 역할:
    - MCP Client의 핵심 컴포넌트 (integrated_api_server.py가 호출)
    - MCP Server 도구들을 LLM을 통해 지능적으로 활용
    - 계획-실행-반성 사이클로 복잡한 분석 질의 처리
    
    주요 특징:
    - 검증된 MCP Server 도구만 사용 (안정성 확보)
    - FastMCP 기반 깔끔한 API 구조 활용
    - 모든 데이터 처리는 DataFrame/SQL 기반
    - 실패 시 자동 재계획 및 대안 전략 수립
    """
    def __init__(self, backend="openai", model=None, **llm_kwargs):
        self.backend = backend
        if model is None:
            model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        self.model = model
        self.llm_kwargs = llm_kwargs
        self.llm = get_llm_client(backend)
        self.df_agent = Text2DFQueryAgent()
        
        print(f"[AgentChain] 🤖 MCP Client 에이전트 초기화 완료")
        print(f"[AgentChain] 🔧 LLM: {backend}/{model}")
        print(f"[AgentChain] 📊 SQL Agent: Text2DFQueryAgent")
        print(f"[AgentChain] 🏗️ MCP Server: mcp_api_v2.py")

    def plan_with_llm(self, question, schema):
        """
        LLM 기반 분석 계획 수립
        - MCP Server 도구들을 고려한 계획 생성
        - 검증된 KOSIS 통계표 우선 사용
        - 단계별 실행 가능한 액션 계획
        """
        system_prompt = f"""
당신은 MCP 아키텍처 기반 데이터 분석 에이전트입니다.

🏗️ MCP Server 도구 (검증됨):
1. fetch_kosis_data - KOSIS 통계자료 직접 조회 (권장)
2. get_stat_list - 통계목록 탐색

🎯 검증된 KOSIS 테이블:
- 인구: orgId="101", tblId="DT_1B040A3", itmId="T20", objL1="00"

📋 MCP 기반 분석 규칙:
1. 인구 관련 질문 → fetch_kosis_data 직접 사용
2. 시점: startPrdDe="2020", endPrdDe="2024" (최근 5년)
3. 다른 주제도 인구 데이터로 대체 분석 가능
4. 모든 데이터는 DataFrame → SQL 테이블로 변환

🔄 워크플로우: MCP Server 도구 호출 → DataFrame 변환 → SQL 분석 → 시각화

JSON 형식으로만 반환하세요:
{{"steps": [
  {{"type": "tool_call", "tool_name": "fetch_kosis_data", "params": {{...}}}},
  {{"type": "query", "description": "MCP 데이터 SQL 분석"}},
  {{"type": "visualization", "description": "결과 시각화"}}
]}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"MCP 기반 분석 요청: {question}"}
        ]
        
        try:
            plan_str = self.llm.chat(messages, model=self.model, max_tokens=500)
            
            # JSON 부분만 추출
            if plan_str.strip().startswith('{'):
                plan_json = json.loads(plan_str)
            else:
                start_idx = plan_str.find('{')
                end_idx = plan_str.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = plan_str[start_idx:end_idx]
                    plan_json = json.loads(json_str)
                else:
                    raise ValueError("JSON을 찾을 수 없음")
            
            steps = plan_json.get("steps", [])
            print(f"[AgentChain] ✅ MCP 계획 수립 성공: {len(steps)}개 단계")
            
        except Exception as e:
            print(f"[AgentChain] ⚠️ LLM 계획 수립 실패: {e}, 기본 MCP 계획 사용")
            # 기본 계획: 검증된 인구 통계 조회 (MCP Server 도구 사용)
            steps = [
                {
                    "type": "tool_call",
                    "description": f"MCP Server를 통한 {question} 관련 인구 통계 조회",
                    "tool_name": "fetch_kosis_data",
                    "params": {
                        "orgId": "101", 
                        "tblId": "DT_1B040A3", 
                        "prdSe": "Y", 
                        "startPrdDe": "2020", 
                        "endPrdDe": "2024",
                        "itmId": "T20",
                        "objL1": "00"
                    }
                },
                {"type": "query", "description": f"MCP 데이터를 기반으로 한 {question} 분석"},
                {"type": "visualization", "description": "MCP 분석 결과 시각화"}
            ]
        
        return steps

    def reflect_and_replan(self, question, schema, history, prev_steps, prev_result, prev_error):
        """
        실패 시 재계획 수립
        - MCP Server 도구 호출 실패 분석
        - 대안 도구나 파라미터 제안
        - 검증된 도구만 사용하도록 제한
        """
        history_str = "\n".join(
            f"{i+1}회차: step={h['step']}, type={h['type']}, result={h['result']}, error={h.get('error','')}"
            for i, h in enumerate(history)
        )
        prev_steps_str = json.dumps(prev_steps, ensure_ascii=False)
        
        system_prompt = f"""
MCP 기반 에이전트 재계획 시스템입니다.

🏗️ 검증된 MCP Server 도구 목록:
{MCP_TOOL_SPEC_STR}

⚠️ **중요 제약사항**:
- 검증된 KOSIS 통계표만 사용 (DT_1B040A3 인구 데이터 우선)
- MCP Server 연동 실패 시 파라미터 단순화
- DEPRECATED 함수나 미검증 도구 사용 금지

🔄 재계획 전략:
1. MCP Server 도구 호출 실패 → 파라미터 간소화
2. 데이터 없음 → 다른 시점이나 지역 시도
3. SQL 오류 → 단순한 쿼리로 변경
"""
        
        user_prompt = f"""
MCP 기반 분석 재계획이 필요합니다.

🔍 이전 시도 이력:
{history_str}

📋 현재 상황:
- 이전 계획: {prev_steps_str}
- 실행 결과: {prev_result}
- MCP 오류: {prev_error}
- 원래 질문: {question}

🎯 요구사항:
- 검증된 MCP Server 도구만 사용
- 이전과 다른 접근 방식 시도
- MCP 실패 원인 분석 후 개선된 계획 제시

JSON 형식으로 새로운 계획을 반환하세요.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            plan_str = self.llm.chat(messages, model=self.model)
            plan_json = json.loads(plan_str)
            steps = plan_json.get("steps", [])
            print(f"[AgentChain] 🔄 MCP 재계획 수립: {len(steps)}개 단계")
        except Exception as e:
            print(f"[AgentChain] ❌ MCP 재계획 실패: {e}")
            steps = []
        return steps

    def execute_step(self, step):
        """
        개별 단계 실행 (MCP Server 도구 호출 포함)
        - tool_call: MCP Server 도구 호출
        - query: DataFrame/SQL 기반 분석
        - visualization: 차트 생성
        """
        step_type = step.get("type")
        desc = step.get("description", "")
        result = None
        step_error = None
        
        try:
            if step_type == "query":
                # SQL 기반 DataFrame 쿼리 실행
                print(f"[AgentChain] 📊 SQL 쿼리 실행: {desc}")
                result = self.df_agent.run(desc)
                step_error = result.get("error")
                
            elif step_type == "visualization":
                # 시각화 단계
                print(f"[AgentChain] 📈 시각화 생성: {desc}")
                result = {"msg": f"시각화({step.get('method', 'chart')}) 단계 완료"}
                
            elif step_type == "tool_call":
                # MCP Server 도구 호출
                tool_name = step.get("tool_name")
                params = step.get("params", {})
                
                print(f"[AgentChain] 🔧 MCP Server 도구 호출: {tool_name}")
                
                if tool_name == "fetch_kosis_data":
                    result = self._execute_fetch_kosis_data(params)
                    step_error = result.get("error")
                    
                elif tool_name == "get_stat_list":
                    result = self._execute_get_stat_list(params)
                    step_error = result.get("error")
                    
                else:
                    result = {"error": f"지원하지 않는 MCP Server 도구: {tool_name}"}
                    step_error = f"알 수 없는 MCP 도구: {tool_name}"
            else:
                result = {"error": f"알 수 없는 step type: {step_type}"}
                step_error = "step type 오류"
                
        except Exception as e:
            result = {"error": f"MCP 단계 실행 오류: {e}"}
            step_error = str(e)
            print(f"[AgentChain] ❌ 단계 실행 오류: {e}")
        
        return {
            "result": result,
            "error": step_error,
            "step_type": step_type,
            "description": desc
        }

    def _execute_fetch_kosis_data(self, params):
        """
        MCP Server의 fetch_kosis_data 도구 실행
        - KOSIS API 호출을 MCP Server에 위임
        - 결과 DataFrame 변환 및 SQL 테이블 등록
        - 에러 처리 및 로깅
        """
        try:
            api_key = os.environ.get("KOSIS_OPEN_API_KEY", "")
            
            # 필수 파라미터 확인
            orgId = params.get("orgId")
            tblId = params.get("tblId")
            
            if not (orgId and tblId):
                return {"error": "MCP Server 호출 실패: 필수 파라미터(orgId, tblId) 누락", "params": params}
            
            print(f"[AgentChain] 🌐 MCP Server → KOSIS API 호출: {orgId}/{tblId}")
            
            # MCP Server 도구 호출
            result = fetch_kosis_data(
                orgId=orgId,
                tblId=tblId,
                prdSe=params.get("prdSe", "Y"),
                startPrdDe=params.get("startPrdDe", ""),
                endPrdDe=params.get("endPrdDe", ""),
                itmId=params.get("itmId", ""),
                objL1=params.get("objL1", ""),
                api_key=api_key
            )
            
            # MCP Server 응답 처리 및 DataFrame 변환
            if "data" in result and result["data"]:
                df = convert_to_dataframe(result)
                if not df.empty:
                    df_name = f"mcp_kosis_{tblId}"
                    self.df_agent.dataframes[df_name] = df
                    table_name = self.df_agent.register_dataframe(df_name, df)
                    
                    print(f"[AgentChain] ✅ MCP 데이터 변환 완료: {len(df)}행 → SQL 테이블 '{table_name}'")
                    
                    return {
                        "msg": f"MCP Server를 통한 KOSIS 데이터 조회 성공: {len(df)}행",
                        "df_shape": df.shape,
                        "df_name": df_name,
                        "sql_table_name": table_name,
                        "mcp_server_response": result.get("count", 0),
                        "data_preview": df.head(3).to_dict('records') if len(df) > 0 else []
                    }
                else:
                    return {"error": "MCP Server에서 데이터를 가져왔지만 DataFrame 변환 실패", "mcp_result": result}
            else:
                return {"error": "MCP Server에서 빈 데이터 반환", "mcp_result": result}
            
        except Exception as e:
            print(f"[AgentChain] ❌ MCP Server 도구 호출 오류: {e}")
            return {"error": f"MCP Server fetch_kosis_data 오류: {e}", "params": params}

    def _execute_get_stat_list(self, params):
        """
        MCP Server의 get_stat_list 도구 실행
        - 통계목록 조회를 MCP Server에 위임
        - 메타데이터 수집 및 분석
        """
        try:
            api_key = os.environ.get("KOSIS_OPEN_API_KEY", "")
            
            print(f"[AgentChain] 🌐 MCP Server → KOSIS 통계목록 조회")
            
            # MCP Server 도구 호출
            result = get_stat_list(
                vwCd=params.get("vwCd", "MT_ZTITLE"),
                parentListId=params.get("parentListId", ""),
                format=params.get("format", "json"),
                api_key=api_key
            )
            
            if "data" in result:
                print(f"[AgentChain] ✅ MCP Server 통계목록 조회 성공: {result.get('count', 0)}개")
                return {
                    "msg": f"MCP Server를 통한 통계목록 조회 성공: {result.get('count', 0)}개",
                    "stat_count": result.get('count', 0),
                    "mcp_server_response": result.get('count', 0),
                    "stat_list_preview": result["data"][:5] if result["data"] else []
                }
            else:
                return {"error": "MCP Server 통계목록 조회 실패", "mcp_result": result}
            
        except Exception as e:
            print(f"[AgentChain] ❌ MCP Server 통계목록 오류: {e}")
            return {"error": f"MCP Server get_stat_list 오류: {e}", "params": params}

    def run(self, question, max_reflection_steps=3):
        """
        MCP 기반 에이전트 메인 실행 함수
        
        워크플로우:
        1. LLM이 질문 분석 → MCP Server 도구 호출 계획 수립
        2. MCP Server 도구 실행 → 외부 데이터 수집
        3. DataFrame 변환 → SQL 테이블 등록
        4. LLM SQL 쿼리 생성 → Text2DFQueryAgent 실행
        5. 결과 분석 → 필요 시 재계획 (최대 3회)
        """
        print(f"[AgentChain] 🚀 MCP 기반 분석 시작: {question}")
        
        # MCP Server 도구 정보를 포함한 스키마 생성
        schema = f"""
🏗️ MCP 아키텍처 기반 분석 환경:
- MCP Client: AgentChain (이 에이전트)
- MCP Server: mcp_api_v2.py (KOSIS API 도구 제공)
- 기존 DataFrame: {list(self.df_agent.dataframes.keys())}

📊 SQL 분석 가능 테이블:
{', '.join(self.df_agent.get_available_tables().keys()) if self.df_agent.get_available_tables() else '없음'}
"""
        
        steps = self.plan_with_llm(question, schema)
        history = []
        error = None
        
        for step_idx, step in enumerate(steps):
            print(f"[AgentChain] 📋 단계 {step_idx+1}/{len(steps)}: {step.get('type')} - {step.get('description', '')}")
            
            execution_result = self.execute_step(step)
            
            history.append({
                "step": step_idx,
                "type": execution_result["step_type"],
                "description": execution_result["description"],
                "result": execution_result["result"],
                "error": execution_result["error"]
            })
            
            # MCP Server 도구 호출이나 SQL 쿼리 실패 시 재계획
            if execution_result["error"] and step["type"] in ["tool_call", "query"]:
                error = execution_result["error"]
                remaining_plan = steps[step_idx+1:]
                
                print(f"[AgentChain] ⚠️ 오류 발생, 재계획 시도: {error}")
                
                for reflection_round in range(max_reflection_steps):
                    print(f"[AgentChain] 🔄 재계획 {reflection_round+1}/{max_reflection_steps}")
                    
                    new_steps = self.reflect_and_replan(question, schema, history, steps, execution_result["result"], error)
                    if not new_steps:
                        print(f"[AgentChain] ❌ 재계획 실패, 중단")
                        break
                        
                    # 첫 번째 새 단계 실행
                    new_step = new_steps[0]
                    new_execution = self.execute_step(new_step)
                    
                    history.append({
                        "step": len(history),
                        "type": new_execution["step_type"], 
                        "description": new_execution["description"],
                        "result": new_execution["result"],
                        "error": new_execution["error"]
                    })
                    
                    # 성공하면 재계획 종료
                    if not new_execution["error"]:
                        print(f"[AgentChain] ✅ 재계획 성공!")
                        error = None
                        break
                    else:
                        error = new_execution["error"]
                        print(f"[AgentChain] ⚠️ 재계획 단계도 실패: {error}")
                break
        
        remaining_plan = steps[len(history):] if len(history) < len(steps) else []
        
        # 최종 결과 요약
        total_dataframes = len(self.df_agent.dataframes)
        mcp_calls = sum(1 for h in history if h["type"] == "tool_call" and not h["error"])
        
        print(f"[AgentChain] 🎯 MCP 분석 완료:")
        print(f"  - 실행된 단계: {len(history)}/{len(steps)}")
        print(f"  - MCP Server 호출: {mcp_calls}회")
        print(f"  - 생성된 DataFrame: {total_dataframes}개")
        print(f"  - 최종 오류: {error or '없음'}")
        
        return {
            "history": history,
            "remaining_plan": remaining_plan,
            "final_result": history[-1]["result"] if history else None,
            "error": error,
            "mcp_summary": {
                "total_steps": len(history),
                "mcp_server_calls": mcp_calls,
                "dataframes_created": total_dataframes,
                "sql_tables_available": list(self.df_agent.get_available_tables().keys())
            }
        } 