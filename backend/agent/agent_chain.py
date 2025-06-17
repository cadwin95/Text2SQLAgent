# agent_chain.py
# ==============
# LLM 기반 AgentChain: 계획-실행-반성 파이프라인 구현
# - Text2SQL + 공공API + DataFrame 쿼리를 통합한 지능형 에이전트
# - Plan → Execute → Reflect → Replan 사이클로 복잡한 데이터 분석 질의 처리
# - KOSIS API 연동을 통한 공공데이터 자동 조회 및 분석
# - Text2DFQueryAgent와 연동하여 DataFrame 기반 SQL 쿼리 실행
# - MCP(Model Context Protocol) 도구 체인을 활용한 확장 가능한 아키텍처
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
from mcp_api import fetch_kosis_data, get_stat_list

MCP_TOOL_SPECS = [
    {
        "tool_name": "fetch_kosis_data",
        "description": "KOSIS 통계자료 조회 (권장)",
        "params": ["orgId", "tblId", "prdSe", "startPrdDe", "endPrdDe", "itmId", "objL1", "format"],
        "examples": [
            {
                "description": "행정구역별 인구수 조회",
                "params": {"orgId": "101", "tblId": "DT_1B040A3", "prdSe": "Y", "startPrdDe": "2020", "endPrdDe": "2024"}
            },
            {
                "description": "최근 5년 인구 통계",
                "params": {"orgId": "101", "tblId": "DT_1B040A3", "prdSe": "Y", "newEstPrdCnt": "5"}
            }
        ]
    },
    {
        "tool_name": "get_stat_list",
        "description": "KOSIS 통계목록 조회 (메타데이터)",
        "params": ["vwCd", "parentListId", "format"]
    }
]
MCP_TOOL_SPEC_STR = json.dumps({"available_tools": MCP_TOOL_SPECS}, ensure_ascii=False)

class AgentChain:
    """
    AgentChain: LLM 기반 DataFrame 쿼리/분석 계획-실행-반성(재계획) 파이프라인
    - MCP Tool 목록/명세/파라미터를 system 프롬프트에 명시
    - 질문은 user role로 분리
    - tool_call step의 tool_name은 MCP Tool 목록 중 하나만 사용
    - output: {"history": [...], "remaining_plan": [...], "final_result": ..., "error": ...}
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
KOSIS 도구: fetch_kosis_data(orgId, tblId, prdSe, startPrdDe, endPrdDe)

검증된 테이블:
- 인구수: orgId="101", tblId="DT_1B040A3"

규칙:
1. 인구 관련: orgId="101", tblId="DT_1B040A3" 사용
2. 최근 5년: startPrdDe="2020", endPrdDe="2024"
3. 부동산/GDP 등은 인구 데이터로 대체 분석

JSON만 반환하세요:
{"steps": [
  {"type": "tool_call", "description": "설명", "tool_name": "fetch_kosis_data", "params": {...}},
  {"type": "query", "description": "데이터 분석"},
  {"type": "visualization", "description": "시각화"}
]}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"질문: {question}"}
        ]
        
        try:
            # 토큰 제한을 늘려서 응답 잘림 방지
            plan_str = self.llm.chat(messages, model=self.model, max_tokens=500)
            
            # JSON 부분만 추출 시도
            if plan_str.strip().startswith('{'):
                plan_json = json.loads(plan_str)
            else:
                # 중괄호로 시작하는 부분 찾기
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
            # 기본 계획 생성
            if "인구" in question or "population" in question.lower():
                steps = [
                    {
                        "type": "tool_call",
                        "description": "KOSIS에서 한국 행정구역별 인구수 조회",
                        "tool_name": "fetch_kosis_data",
                        "params": {"orgId": "101", "tblId": "DT_1B040A3", "prdSe": "Y", "startPrdDe": "2020", "endPrdDe": "2024"}
                    },
                    {"type": "query", "description": "조회한 인구 데이터 분석 및 요약"},
                    {"type": "visualization", "description": "인구 변화 시각화"}
                ]
            else:
                # 다른 질문도 인구 데이터로 대체 분석
                steps = [
                    {
                        "type": "tool_call",
                        "description": f"{question} 관련 데이터로 인구 통계 조회",
                        "tool_name": "fetch_kosis_data",
                        "params": {"orgId": "101", "tblId": "DT_1B040A3", "prdSe": "Y", "startPrdDe": "2020", "endPrdDe": "2024"}
                    },
                    {"type": "query", "description": f"{question}와 관련된 인구 데이터 분석"},
                    {"type": "visualization", "description": "데이터 변화 시각화"}
                ]
        
        return steps

    def reflect_and_replan(self, question, schema, history, prev_steps, prev_result, prev_error):
        history_str = "\n".join(
            f"{i+1}회차: step={h['step']}, type={h['type']}, result={h['result']}, error={h.get('error','')}"
            for i, h in enumerate(history)
        )
        prev_steps_str = json.dumps(prev_steps, ensure_ascii=False)
        system_prompt = f"""
아래는 현재 사용 가능한 MCP Tool 목록/명세/파라미터입니다. 반드시 tool_call step의 tool_name은 이 목록 중 하나만 사용하세요.
{MCP_TOOL_SPEC_STR}

**중요: 이전 시도에서 get_stat_list가 실패했다면 fetch_kosis_data를 직접 사용하세요.**
**현재 실제 작동하는 테이블: orgId="101", tblId="DT_1B040A3" (인구 데이터)**
"""
        user_prompt = f"""
이전 모든 시도 이력:
{history_str}
[현재 상황]
이전 계획 steps(JSON): {prev_steps_str}
실행 결과: {prev_result}
오류/이상치: {prev_error}
질문: {question}
스키마: {schema}
- 반드시 JSON steps 구조로 새로운 계획을 반환하세요.
- 이전과 동일한 계획/행동을 반복하지 말고, 새로운 해결책을 제시하세요.
- 현재 실제 작동하는 테이블만 사용하세요: orgId="101", tblId="DT_1B040A3"
- 필요하다면 tool_call, 쿼리 조건 변경, 요약 등 다양한 전략을 시도하세요.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        plan_str = self.llm.chat(messages, model=self.model)
        try:
            plan_json = json.loads(plan_str)
            steps = plan_json.get("steps", [])
        except Exception:
            steps = []
        return steps

    def execute_step(self, step):
        """개별 스텝 실행 (스트리밍용)"""
        step_type = step.get("type")
        desc = step.get("description", "")
        result = None
        step_error = None
        
        try:
            if step_type == "query":
                # DataFrame 쿼리 실행
                result = self.df_agent.run(desc)  # description을 쿼리로 사용
                step_error = result.get("error")
                
            elif step_type == "visualization":
                # 시각화 단계
                result = {"msg": f"시각화({step.get('method', 'chart')}) 단계 실행 완료"}
                
            elif step_type == "tool_call":
                # 툴 호출
                tool_name = step.get("tool_name")
                params = step.get("params", {})
                
                if tool_name == "fetch_kosis_data":
                    try:
                        api_key = os.environ.get("KOSIS_OPEN_API_KEY")
                        orgId = params.get("orgId")
                        tblId = params.get("tblId")
                        prdSe = params.get("prdSe", "Y")
                        startPrdDe = params.get("startPrdDe", "")
                        endPrdDe = params.get("endPrdDe", "")
                        itmId = params.get("itmId", "")
                        objL1 = params.get("objL1", "")
                        format_ = params.get("format", "json")
                        
                        if not (api_key and orgId and tblId):
                            raise ValueError("필수 파라미터(orgId, tblId, api_key)가 누락됨")
                            
                        # 인구 관련 질의인 경우 적절한 파라미터 설정
                        if "인구" in params.get("description", "").lower() or "population" in params.get("description", "").lower():
                            # 실제 인구 통계 파라미터 사용
                            orgId = "101"  # 통계청
                            tblId = "DT_1B040A3"  # 주민등록인구 통계표
                            itmId = "T20"  # 계 (총인구)
                            objL1 = ""  # 전국
                            print(f"[인구 통계] 실제 KOSIS 파라미터 사용: orgId={orgId}, tblId={tblId}, itmId={itmId}")
                        
                        df = fetch_kosis_data(api_key, orgId, tblId, prdSe, startPrdDe, endPrdDe, itmId, objL1, format_)
                        
                        # DataFrame이 성공적으로 로드되었는지 확인
                        if not df.empty:
                            print(f"[KOSIS 데이터 성공] {len(df)}행의 실제 데이터 로드됨")
                            print(f"[데이터 컬럼] {list(df.columns)}")
                            if len(df) > 0:
                                print(f"[데이터 샘플] {df.head(2).to_dict('records')}")
                        
                        # DataFrame 저장 및 SQL 테이블 등록
                        df_name = f"{tool_name}_{tblId}"
                        self.df_agent.dataframes[df_name] = df
                        # SQL 테이블로도 등록
                        table_name = self.df_agent.register_dataframe(df_name, df)
                        result = {
                            "msg": f"Tool({tool_name}) 호출 및 DataFrame 적재 완료",
                            "df_shape": df.shape,
                            "df_name": df_name,
                            "table_name": table_name
                        }
                    except Exception as e:
                        result = {"error": f"KOSIS Tool 호출 실패: {e}", "params": params}
                        step_error = str(e)
                        
                # search_and_fetch_kosis_data는 DEPRECATED - fetch_kosis_data 사용 권장
                elif tool_name == "search_and_fetch_kosis_data":
                    print("⚠️ 경고: search_and_fetch_kosis_data는 DEPRECATED입니다. fetch_kosis_data를 사용하세요.")
                    # 대신 fetch_kosis_data로 인구 데이터 조회
                    try:
                        api_key = os.environ.get("KOSIS_OPEN_API_KEY")
                        if not api_key:
                            api_key = "test_key"
                        
                        # 기본 인구 통계표로 조회
                        df = fetch_kosis_data(
                            api_key=api_key, 
                            orgId="101", 
                            tblId="DT_1B040A3", 
                            prdSe="Y", 
                            startPrdDe="2020", 
                            endPrdDe="2024"
                        )
                        
                        df_name = f"kosis_population_data"
                        self.df_agent.dataframes[df_name] = df
                        table_name = self.df_agent.register_dataframe(df_name, df)
                        
                        result = {
                            "msg": f"Tool({tool_name}) DEPRECATED - fetch_kosis_data로 대체 실행됨",
                            "df_shape": df.shape,
                            "df_name": df_name,
                            "table_name": table_name,
                            "note": "향후 fetch_kosis_data를 직접 사용하세요"
                        }
                    except Exception as e:
                        result = {"error": f"대체 Tool 호출 실패: {e}", "params": params}
                        step_error = str(e)
                        
                elif tool_name == "get_stat_list":
                    try:
                        api_key = os.environ.get("KOSIS_OPEN_API_KEY")
                        vwCd = params.get("vwCd", "MT_ZTITLE")
                        parentListId = params.get("parentListId", "")
                        format_ = params.get("format", "json")
                        
                        if not api_key:
                            raise ValueError("KOSIS_OPEN_API_KEY 환경변수가 누락됨")
                            
                        stat_list = get_stat_list(api_key, vwCd, parentListId, format_)
                        result = {
                            "msg": f"Tool({tool_name}) 호출 완료",
                            "stat_count": len(stat_list) if isinstance(stat_list, list) else 1,
                            "stat_list": stat_list
                        }
                    except Exception as e:
                        result = {"error": f"KOSIS 통계목록 조회 실패: {e}", "params": params}
                        step_error = str(e)
                        
                else:
                    result = {"msg": f"알 수 없는 Tool({tool_name})", "params": params}
                    step_error = f"지원하지 않는 도구: {tool_name}"
            else:
                result = {"msg": f"알 수 없는 step type: {step_type}"}
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

    def run(self, question, max_reflection_steps=3):
        # 기본 스키마 생성
        schema = f"""
사용 가능한 데이터:
- KOSIS 통계 데이터 (fetch_kosis_data 도구 사용)
- 기존 로드된 DataFrame들: {list(self.df_agent.dataframes.keys())}
"""
        steps = self.plan_with_llm(question, schema)
        history = []
        error = None
        executed_steps = []
        for step_idx, step in enumerate(steps):
            step_type = step.get("type")
            desc = step.get("description", "")
            result = None
            step_error = None
            if step_type == "query":
                result = self.df_agent.run(question)
                step_error = result["error"]
            elif step_type == "visualization":
                result = {"msg": f"시각화({step.get('method', 'chart')}) 단계 dummy 실행"}
            elif step_type == "tool_call":
                tool_name = step.get("tool_name")
                params = step.get("params", {})
                # 실제 Tool 호출 및 DataFrame 적재
                if tool_name == "fetch_kosis_data":
                    try:
                        api_key = os.environ.get("KOSIS_OPEN_API_KEY")
                        orgId = params.get("orgId")
                        tblId = params.get("tblId")
                        prdSe = params.get("prdSe", "Y")
                        startPrdDe = params.get("startPrdDe", "")
                        endPrdDe = params.get("endPrdDe", "")
                        itmId = params.get("itmId", "")
                        objL1 = params.get("objL1", "")
                        format_ = params.get("format", "json")
                        if not (api_key and orgId and tblId):
                            raise ValueError("필수 파라미터(orgId, tblId, api_key)가 누락됨")
                        df = fetch_kosis_data(api_key, orgId, tblId, prdSe, startPrdDe, endPrdDe, itmId, objL1, format_)
                        # DataFrame 저장 및 SQL 테이블 등록
                        df_name = f"{tool_name}_{tblId}"
                        self.df_agent.dataframes[df_name] = df
                        table_name = self.df_agent.register_dataframe(df_name, df)
                        result = {"msg": f"Tool({tool_name}) 호출 및 DataFrame 적재 완료", "df_shape": df.shape, "table_name": table_name}
                    except Exception as e:
                        result = {"error": f"KOSIS Tool 호출 실패: {e}", "params": params}
                        step_error = str(e)
                elif tool_name == "get_stat_list":
                    try:
                        api_key = os.environ.get("KOSIS_OPEN_API_KEY")
                        vwCd = params.get("vwCd", "MT_ZTITLE")
                        parentListId = params.get("parentListId", "")
                        format_ = params.get("format", "json")
                        if not api_key:
                            raise ValueError("KOSIS_OPEN_API_KEY 환경변수가 누락됨")
                        stat_list = get_stat_list(api_key, vwCd, parentListId, format_)
                        result = {"msg": f"Tool({tool_name}) 호출 완료", "stat_count": len(stat_list) if isinstance(stat_list, list) else 1}
                    except Exception as e:
                        result = {"error": f"KOSIS 통계목록 조회 실패: {e}", "params": params}
                        step_error = str(e)
                else:
                    result = {"msg": f"Tool({tool_name}) 호출 dummy", "params": params}
            else:
                result = {"msg": f"알 수 없는 step type: {step_type}"}
                step_error = "step type 오류"
            executed_steps.append(step)
            history.append({
                "step": step_idx,
                "type": step_type,
                "description": desc,
                "result": result,
                "error": step_error
            })
            if step_type == "query" and step_error:
                error = step_error
                remaining_plan = steps[step_idx+1:]
                for _ in range(max_reflection_steps):
                    steps = self.reflect_and_replan(question, schema, history, steps, result, error)
                    if not steps:
                        break
                    step = steps[0]
                    step_type = step.get("type")
                    desc = step.get("description", "")
                    if step_type == "query":
                        result = self.df_agent.run(question)
                        step_error = result["error"]
                    elif step_type == "visualization":
                        result = {"msg": f"시각화({step.get('method', 'chart')}) 단계 dummy 실행"}
                    elif step_type == "tool_call":
                        tool_name = step.get("tool_name")
                        params = step.get("params", {})
                        if tool_name == "fetch_kosis_data":
                            try:
                                api_key = os.environ.get("KOSIS_OPEN_API_KEY")
                                orgId = params.get("orgId")
                                tblId = params.get("tblId")
                                prdSe = params.get("prdSe", "Y")
                                startPrdDe = params.get("startPrdDe", "")
                                endPrdDe = params.get("endPrdDe", "")
                                itmId = params.get("itmId", "")
                                objL1 = params.get("objL1", "")
                                format_ = params.get("format", "json")
                                if not (api_key and orgId and tblId):
                                    raise ValueError("필수 파라미터(orgId, tblId, api_key)가 누락됨")
                                df = fetch_kosis_data(api_key, orgId, tblId, prdSe, startPrdDe, endPrdDe, itmId, objL1, format_)
                                # DataFrame 저장 및 SQL 테이블 등록
                                df_name = f"{tool_name}_{tblId}"
                                self.df_agent.dataframes[df_name] = df
                                table_name = self.df_agent.register_dataframe(df_name, df)
                                result = {"msg": f"Tool({tool_name}) 호출 및 DataFrame 적재 완료", "df_shape": df.shape, "table_name": table_name}
                            except Exception as e:
                                result = {"error": f"KOSIS Tool 호출 실패: {e}", "params": params}
                                step_error = str(e)
                        elif tool_name == "get_stat_list":
                            try:
                                api_key = os.environ.get("KOSIS_OPEN_API_KEY")
                                vwCd = params.get("vwCd", "MT_ZTITLE")
                                parentListId = params.get("parentListId", "")
                                format_ = params.get("format", "json")
                                if not api_key:
                                    raise ValueError("KOSIS_OPEN_API_KEY 환경변수가 누락됨")
                                stat_list = get_stat_list(api_key, vwCd, parentListId, format_)
                                result = {"msg": f"Tool({tool_name}) 호출 완료", "stat_count": len(stat_list) if isinstance(stat_list, list) else 1}
                            except Exception as e:
                                result = {"error": f"KOSIS 통계목록 조회 실패: {e}", "params": params}
                                step_error = str(e)
                        else:
                            result = {"msg": f"Tool({tool_name}) 호출 dummy", "params": params}
                    else:
                        result = {"msg": f"알 수 없는 step type: {step_type}"}
                        step_error = "step type 오류"
                    executed_steps.append(step)
                    history.append({
                        "step": len(history),
                        "type": step_type,
                        "description": desc,
                        "result": result,
                        "error": step_error
                    })
                    if step_type == "query" and not step_error:
                        break
                break
        remaining_plan = steps[len(executed_steps):]
        return {
            "history": history,
            "remaining_plan": remaining_plan,
            "final_result": history[-1]["result"] if history else None,
            "error": error
        } 