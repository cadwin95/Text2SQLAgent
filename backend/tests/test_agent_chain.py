# test_agent_chain.py
# ==================
# AgentChain 모듈 단위/통합 테스트 파일
# - 계획-실행-반성 파이프라인의 정상 동작/예외 처리/응답 구조 검증
# - Text2SQL + KOSIS API + DataFrame 쿼리 통합 시나리오 테스트
# - Tool 호출, DataFrame 관리, 오류 복구 등 핵심 기능 검증
# - 자동화 테스트/CI 연동, MCP 파이프라인 안정성 보장 목적
# - OpenAI API 기반 실제 LLM 호출을 통한 End-to-End 테스트
# - 자세한 설계/구현 규칙은 .cursor/rules/rl-text2sql-public-api.md 참고

import os
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent_chain import AgentChain

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_agent_chain_end_to_end():
    """
    AgentChain이 실제 질문에 대해 계획→실행→반성(재계획)→최종 결과까지 end-to-end로 동작하는지 검증
    - 결과: history, remaining_plan, final_result, error 등 dict 구조
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    chain = AgentChain(backend="openai", model=model)
    question = "한국의 인구 통계를 분석해주세요"
    result = chain.run(question)
    assert isinstance(result, dict)
    assert "history" in result and isinstance(result["history"], list)
    assert "remaining_plan" in result
    assert "final_result" in result and isinstance(result["final_result"], dict)
    assert "error" in result
    # 최소한 하나의 step은 실행되어야 함
    assert len(result["history"]) >= 1
    # history 각 step 구조 검증
    for step in result["history"]:
        assert "step" in step  # "plan" 대신 "step" 키 사용
        assert "result" in step and isinstance(step["result"], dict)
        assert "error" in step 

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_agent_chain_structured_plan():
    """
    AgentChain이 구조화된 계획(JSON steps) 기반으로 각 step을 실행하고, history/remaining_plan을 올바르게 반환하는지 검증
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    chain = AgentChain(backend="openai", model=model)
    question = "한국의 GDP 성장률 추이를 분석해주세요"
    result = chain.run(question)
    assert isinstance(result, dict)
    assert "history" in result and isinstance(result["history"], list)
    assert "remaining_plan" in result and isinstance(result["remaining_plan"], list)
    assert "final_result" in result
    assert "error" in result
    # 최소한 하나의 step은 실행되어야 함
    assert len(result["history"]) >= 1
    # history 각 step 구조 검증
    for step in result["history"]:
        assert "step" in step
        assert "type" in step
        assert step["type"] in ("query", "visualization", "tool_call")
        assert "description" in step
        assert "result" in step
        assert "error" in step
    # remaining_plan도 step 리스트
    for step in result["remaining_plan"]:
        assert "type" in step and "description" in step 

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_agent_chain_tool_execution():
    """
    AgentChain의 tool_call step이 올바르게 실행되고 DataFrame에 저장되는지 검증
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    chain = AgentChain(backend="openai", model=model)
    
    # tool_call step 직접 실행 테스트
    step = {
        "type": "tool_call",
        "description": "KOSIS에서 인구 데이터 조회",
        "tool_name": "fetch_kosis_data",
        "params": {
            "orgId": "101",
            "tblId": "DT_1B040A3",
            "prdSe": "Y",
            "startPrdDe": "2020",
            "endPrdDe": "2024"
        }
    }
    
    result = chain.execute_step(step)
    assert isinstance(result, dict)
    assert "result" in result
    assert "error" in result
    assert "step_type" in result
    assert result["step_type"] == "tool_call"

def test_agent_chain_dataframe_management():
    """
    AgentChain의 DataFrame 관리 기능 테스트
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    chain = AgentChain(backend="openai", model=model)
    
    # 초기 상태 확인
    assert isinstance(chain.df_agent.dataframes, dict)
    initial_df_count = len(chain.df_agent.dataframes)
    
    # DataFrame 추가 후 개수 확인 (tool 호출 시뮬레이션)
    import pandas as pd
    test_df = pd.DataFrame({'year': [2020, 2021], 'population': [50000000, 51000000]})
    chain.df_agent.dataframes['test_data'] = test_df
    
    assert len(chain.df_agent.dataframes) == initial_df_count + 1
    assert 'test_data' in chain.df_agent.dataframes 