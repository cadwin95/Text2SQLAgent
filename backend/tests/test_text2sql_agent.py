import os
import pytest
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.text2sql_agent import Text2DFQueryAgent

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_text2df_query_agent_success():
    """
    Text2DFQueryAgent가 DataFrame 기반 쿼리 생성→실행→구조화 결과 반환하는지 검증
    - 예시: 샘플 DataFrame에서 평균값 계산
    - 결과: query_code, columns, rows, error
    """
    agent = Text2DFQueryAgent(backend="openai")
    
    # 테스트용 DataFrame 추가
    test_data = pd.DataFrame({
        'year': [2020, 2021, 2022, 2023],
        'population': [51780000, 51830000, 51880000, 51930000],
        'gdp_growth': [2.1, 3.2, 2.8, 3.5]
    })
    agent.dataframes['test_data'] = test_data
    
    question = "인구 데이터의 평균 GDP 성장률을 계산해주세요"
    result = agent.run(question)
    
    assert isinstance(result, dict)
    assert "query_code" in result
    assert "columns" in result and isinstance(result["columns"], list)
    assert "rows" in result and isinstance(result["rows"], list)
    assert "error" in result
    assert result["error"] is None  # 성공 시 error는 None이어야 함

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_text2df_query_agent_with_empty_dataframes():
    """
    DataFrame이 없는 상태에서 쿼리 실행 시 적절한 error 반환하는지 검증
    """
    agent = Text2DFQueryAgent(backend="openai")
    
    question = "데이터를 분석해주세요"
    result = agent.run(question)
    
    assert isinstance(result, dict)
    assert "error" in result
    # DataFrame이 없으면 에러가 발생할 수 있음 (또는 적절한 안내 메시지)

def test_text2df_query_agent_dataframe_storage():
    """
    DataFrame 저장소가 올바르게 작동하는지 검증
    """
    agent = Text2DFQueryAgent(backend="openai")
    
    # DataFrame 추가
    df1 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df2 = pd.DataFrame({'x': [7, 8, 9], 'y': [10, 11, 12]})
    
    agent.dataframes['test_df1'] = df1
    agent.dataframes['test_df2'] = df2
    
    # DataFrame이 올바르게 저장되었는지 확인
    assert 'test_df1' in agent.dataframes
    assert 'test_df2' in agent.dataframes
    assert len(agent.dataframes) == 2
    assert agent.dataframes['test_df1'].shape == (3, 2)
    assert agent.dataframes['test_df2'].shape == (3, 2)

def test_get_dataframe_info():
    """
    _get_dataframe_info 메서드가 올바른 스키마 정보를 반환하는지 검증
    """
    agent = Text2DFQueryAgent(backend="openai")
    
    # 빈 상태 테스트
    info = agent._get_dataframe_info()
    assert "사용 가능한 DataFrame이 없습니다." in info
    
    # DataFrame 추가 후 테스트
    test_data = pd.DataFrame({
        'year': [2020, 2021, 2022],
        'value': [100.5, 200.7, 300.2],
        'category': ['A', 'B', 'C']
    })
    agent.dataframes['test_data'] = test_data
    
    info = agent._get_dataframe_info()
    
    # 기본 정보 확인
    assert "DataFrame 'test_data':" in info
    assert "크기: 3행 x 3열" in info
    assert "year" in info and "value" in info and "category" in info
    
    # 데이터 타입 정보 확인
    assert "int" in info  # year 컬럼
    assert "float" in info  # value 컬럼
    assert "object" in info  # category 컬럼
    
    # 기본 정보 확인
    assert "2020" in info and "100.5" in info and "A" in info
    
    # 통계 정보 확인 (숫자형 컬럼)
    assert "범위" in info and "평균" in info

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")  
def test_text2df_query_agent_multiple_dataframes():
    """
    여러 DataFrame을 사용한 복합 쿼리가 작동하는지 검증
    """
    agent = Text2DFQueryAgent(backend="openai")
    
    # 여러 DataFrame 추가
    df_population = pd.DataFrame({
        'year': [2020, 2021, 2022],
        'population': [50000000, 50500000, 51000000]
    })
    df_gdp = pd.DataFrame({
        'year': [2020, 2021, 2022], 
        'gdp': [1.8e12, 1.9e12, 2.0e12]
    })
    
    agent.dataframes['population'] = df_population
    agent.dataframes['gdp'] = df_gdp
    
    question = "인구와 GDP 데이터를 결합하여 1인당 GDP를 계산해주세요"
    result = agent.run(question)
    
    assert isinstance(result, dict)
    assert "query_code" in result
    assert "columns" in result
    assert "rows" in result
    # 복합 쿼리는 성공하거나 적절한 에러 메시지를 반환해야 함 

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_text2df_query_agent_series_result():
    """
    pandas Series 결과를 올바르게 처리하는지 검증
    """
    agent = Text2DFQueryAgent(backend="openai")
    
    sample_data = pd.DataFrame({
        'category': ['A', 'B', 'A', 'C', 'B'],
        'value': [10, 20, 15, 30, 25]
    })
    agent.dataframes['test_data'] = sample_data
    
    question = "카테고리별 개수를 세어주세요"
    result = agent.run(question)
    
    assert isinstance(result, dict)
    assert "query_code" in result
    assert "columns" in result
    assert "rows" in result
    
    if result["error"] is None:
        # Series 결과는 index와 value로 변환되어야 함
        assert len(result["columns"]) == 2
        assert "index" in result["columns"][0] or "value" in result["columns"][1]

@pytest.mark.skipif('OPENAI_API_KEY' not in os.environ, reason="OPENAI_API_KEY 환경변수 필요")
def test_text2df_query_agent_markdown_code_cleanup():
    """
    생성된 코드에서 마크다운 코드 블록이 올바르게 제거되는지 검증
    """
    agent = Text2DFQueryAgent(backend="openai")
    
    sample_data = pd.DataFrame({
        'x': [1, 2, 3],
        'y': [4, 5, 6]
    })
    agent.dataframes['data'] = sample_data
    
    question = "기본 통계를 보여주세요"
    result = agent.run(question)
    
    assert isinstance(result, dict)
    
    if result["error"] is None and result["query_code"]:
        # 마크다운 코드 블록이 제거되었는지 확인
        assert not result["query_code"].startswith("```")
        assert not result["query_code"].endswith("```")
        assert "```python" not in result["query_code"] 