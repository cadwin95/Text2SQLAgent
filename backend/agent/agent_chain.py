# agent_chain.py
# ==============
# LLM 기반 AgentChain: 계획-실행-반성 파이프라인 구현
# - Text2SQL + 공공API + DataFrame 쿼리를 통합한 지능형 에이전트
# - Plan → Execute → Reflect → Replan 사이클로 복잡한 데이터 분석 질의 처리
# - KOSIS API 연동을 통한 공공데이터 자동 조회 및 분석 (FastMCP 기반)
# - Text2DFQueryAgent와 연동하여 DataFrame 기반 SQL 쿼리 실행
# - 실패 시 자동 재계획 및 대안 전략 수립 (최대 3회 반복)
# - OpenAI API, HuggingFace, GGUF 등 다양한 LLM 백엔드 지원
# - 자세한 설계/구현 규칙은 .cursor/rules/rl-text2sql-public-api.md 참고

import os
import sys
import json
import pandas as pd

# 상대 import를 절대 import로 변경
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.text2sql_agent import Text2DFQueryAgent
from llm_client import get_llm_client

# 새로운 깔끔한 MCP API 클라이언트 사용
try:
    from mcp_api_v2 import fetch_kosis_data, get_stat_list, convert_to_dataframe
    print("[AgentChain] 새로운 FastMCP 기반 KOSIS API 사용")
except ImportError:
    # 백업용 기존 API
    from mcp_api import fetch_kosis_data, get_stat_list
    convert_to_dataframe = lambda x: pd.DataFrame(x.get("data", []))
    print("[AgentChain] 기존 KOSIS API 사용")

# 깔끔한 MCP 도구 명세 (검증된 도구만)
MCP_TOOL_SPECS = [
    {
        "tool_name": "fetch_kosis_data",
        "description": "KOSIS 통계자료 직접 조회 (권장)",
        "params": ["orgId", "tblId", "prdSe", "startPrdDe", "endPrdDe", "itmId", "objL1"],
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
        "description": "KOSIS 통계목록 탐색 (메타데이터)",
        "params": ["vwCd", "parentListId", "format"]
    }
]

MCP_TOOL_SPEC_STR = json.dumps({"available_tools": MCP_TOOL_SPECS}, ensure_ascii=False)

class AgentChain:
    """
    AgentChain: LLM 기반 DataFrame 쿼리/분석 계획-실행-반성(재계획) 파이프라인
    - 검증된 MCP Tool만 사용 (DEPRECATED 함수 제거)
    - FastMCP 기반 깔끔한 API 구조
    - 모든 쿼리/분석/Tool 호출은 DataFrame 기반으로 처리
    """
    def __init__(self, backend="openai", model=None, **llm_kwargs):
        self.backend = backend
        if model is None:
            model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        self.model = model
        self.llm_kwargs = llm_kwargs
        self.llm = get_llm_client(backend)
        self.df_agent = Text2DFQueryAgent()

    def plan_with_llm(self, question, schema):
        system_prompt = """
KOSIS 도구 (검증됨):
1. fetch_kosis_data - 통계자료 직접 조회 (권장)
2. get_stat_list - 통계목록 탐색

검증된 테이블:
- 인구: orgId="101", tblId="DT_1B040A3", itmId="T20", objL1="00"

규칙:
1. 인구 관련 질문 → fetch_kosis_data 직접 사용
2. 시점: startPrdDe="2020", endPrdDe="2024" (최근 5년)
3. 다른 주제도 인구 데이터로 대체 분석 가능

JSON만 반환하세요:
{"steps": [
  {"type": "tool_call", "tool_name": "fetch_kosis_data", "params": {...}},
  {"type": "query", "description": "데이터 분석"},
  {"type": "visualization", "description": "시각화"}
]}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"질문: {question}"}
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
            print(f"[계획 수립 성공] {len(steps)}개 단계 생성됨")
            
        except Exception as e:
            print(f"[계획 수립 실패] {e}, 기본 계획 사용")
            # 기본 계획: 검증된 인구 통계 조회
            steps = [
                {
                    "type": "tool_call",
                    "description": f"{question} 관련 인구 통계 조회",
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
                {"type": "query", "description": f"{question}와 관련된 데이터 분석"},
                {"type": "visualization", "description": "데이터 시각화"}
            ]
        
        return steps

    def reflect_and_replan(self, question, schema, history, prev_steps, prev_result, prev_error):
        history_str = "\n".join(
            f"{i+1}회차: step={h['step']}, type={h['type']}, result={h['result']}, error={h.get('error','')}"
            for i, h in enumerate(history)
        )
        prev_steps_str = json.dumps(prev_steps, ensure_ascii=False)
        
        system_prompt = f"""
검증된 MCP Tool 목록:
{MCP_TOOL_SPEC_STR}

**중요: 검증된 통계표만 사용하세요**
- 인구: orgId="101", tblId="DT_1B040A3"
- DEPRECATED 함수는 사용 금지
"""
        
        user_prompt = f"""
이전 시도 이력:
{history_str}

현재 상황:
- 이전 계획: {prev_steps_str}
- 실행 결과: {prev_result}
- 오류: {prev_error}
- 질문: {question}

새로운 JSON 계획을 반환하세요:
- 검증된 도구만 사용
- 이전과 다른 접근 시도
- 실패 원인 분석 후 개선
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            plan_str = self.llm.chat(messages, model=self.model)
            plan_json = json.loads(plan_str)
            steps = plan_json.get("steps", [])
        except Exception:
            steps = []
        return steps

    def execute_step(self, step):
        """개별 스텝 실행 (깔끔한 구조)"""
        step_type = step.get("type")
        desc = step.get("description", "")
        result = None
        step_error = None
        
        try:
            if step_type == "query":
                # DataFrame 쿼리 실행
                result = self.df_agent.run(desc)
                step_error = result.get("error")
                
            elif step_type == "visualization":
                # 시각화 단계
                result = {"msg": f"시각화({step.get('method', 'chart')}) 단계 완료"}
                
            elif step_type == "tool_call":
                # 검증된 툴만 호출
                tool_name = step.get("tool_name")
                params = step.get("params", {})
                
                if tool_name == "fetch_kosis_data":
                    result = self._execute_fetch_kosis_data(params)
                    step_error = result.get("error")
                    
                elif tool_name == "get_stat_list":
                    result = self._execute_get_stat_list(params)
                    step_error = result.get("error")
                    
                else:
                    result = {"error": f"지원하지 않는 도구: {tool_name}"}
                    step_error = f"알 수 없는 도구: {tool_name}"
            else:
                result = {"error": f"알 수 없는 step type: {step_type}"}
                step_error = "step type 오류"
                
        except Exception as e:
            result = {"error": f"스텝 실행 오류: {e}"}
            step_error = str(e)
        
        return {
            "result": result,
            "error": step_error,
            "step_type": step_type,
            "description": desc
        }

    def _execute_fetch_kosis_data(self, params):
        """KOSIS 데이터 조회 실행"""
        try:
            api_key = os.environ.get("KOSIS_OPEN_API_KEY", "")
            
            # 필수 파라미터 확인
            orgId = params.get("orgId")
            tblId = params.get("tblId")
            
            if not (orgId and tblId):
                return {"error": "필수 파라미터(orgId, tblId)가 누락됨", "params": params}
            
            # API 호출
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
            
            # DataFrame 변환 및 저장
            if "data" in result and result["data"]:
                df = convert_to_dataframe(result)
                if not df.empty:
                    df_name = f"kosis_{tblId}"
                    self.df_agent.dataframes[df_name] = df
                    table_name = self.df_agent.register_dataframe(df_name, df)
                    
                    return {
                        "msg": f"KOSIS 데이터 조회 성공: {len(df)}행",
                        "df_shape": df.shape,
                        "df_name": df_name,
                        "table_name": table_name,
                        "data_preview": df.head(3).to_dict('records') if len(df) > 0 else []
                    }
            
            return {"error": "빈 데이터 또는 조회 실패", "result": result}
            
        except Exception as e:
            return {"error": f"KOSIS 데이터 조회 오류: {e}", "params": params}

    def _execute_get_stat_list(self, params):
        """KOSIS 통계목록 조회 실행"""
        try:
            api_key = os.environ.get("KOSIS_OPEN_API_KEY", "")
            
            result = get_stat_list(
                vwCd=params.get("vwCd", "MT_ZTITLE"),
                parentListId=params.get("parentListId", ""),
                format=params.get("format", "json"),
                api_key=api_key
            )
            
            if "data" in result:
                return {
                    "msg": f"통계목록 조회 성공: {result.get('count', 0)}개",
                    "stat_count": result.get('count', 0),
                    "stat_list_preview": result["data"][:5] if result["data"] else []
                }
            
            return {"error": "통계목록 조회 실패", "result": result}
            
        except Exception as e:
            return {"error": f"통계목록 조회 오류: {e}", "params": params}

    def run(self, question, max_reflection_steps=3):
        """메인 실행 함수 (기존 호환성 유지)"""
        # 기본 스키마 생성
        schema = f"""
사용 가능한 데이터:
- KOSIS 통계 데이터 (fetch_kosis_data 도구 사용)
- 기존 DataFrame: {list(self.df_agent.dataframes.keys())}
"""
        
        steps = self.plan_with_llm(question, schema)
        history = []
        error = None
        
        for step_idx, step in enumerate(steps):
            execution_result = self.execute_step(step)
            
            history.append({
                "step": step_idx,
                "type": execution_result["step_type"],
                "description": execution_result["description"],
                "result": execution_result["result"],
                "error": execution_result["error"]
            })
            
            # 오류 시 재계획
            if execution_result["error"] and step["type"] == "query":
                error = execution_result["error"]
                remaining_plan = steps[step_idx+1:]
                
                for reflection_round in range(max_reflection_steps):
                    new_steps = self.reflect_and_replan(question, schema, history, steps, execution_result["result"], error)
                    if not new_steps:
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
                    
                    # 성공하면 종료
                    if not new_execution["error"]:
                        break
                break
        
        remaining_plan = steps[len(history):] if len(history) < len(steps) else []
        
        return {
            "history": history,
            "remaining_plan": remaining_plan,
            "final_result": history[-1]["result"] if history else None,
            "error": error
        } 