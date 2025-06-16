import pandas as pd
import numpy as np
import os
import sys

# 상대 import를 절대 import로 변경
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_client import get_llm_client
from mcp_api import fetch_kosis_data

class Text2DFQueryAgent:
    """
    자연어 질의 → pandas 쿼리/분석 코드 생성/실행 → 구조화된 결과 반환
    - reflection scheduling/분석 등은 통합 AgentChain에서 담당
    - output: {"query_code": ..., "columns": [...], "rows": [...], "error": ...}
    """
    def __init__(self, backend="openai", model=None, **llm_kwargs):
        self.backend = backend
        if model is None:
            model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        self.model = model
        self.llm_kwargs = llm_kwargs
        self.llm = get_llm_client(backend)
        self.dataframes = {}  # Tool/API 호출 결과 DataFrame 저장용

    def _get_dataframe_info(self):
        """DataFrame의 구조와 내용을 상세 분석하여 LLM에게 제공"""
        if not self.dataframes:
            return "현재 로드된 DataFrame이 없습니다."
        
        info_str = f"총 {len(self.dataframes)}개의 DataFrame이 로드되었습니다:\n\n"
        
        for name, df in self.dataframes.items():
            info_str += f"**DataFrame: {name}**\n"
            info_str += f"- 크기: {df.shape[0]}행 × {df.shape[1]}열\n"
            info_str += f"- 컬럼: {list(df.columns)}\n"
            info_str += f"- 데이터 타입: {dict(df.dtypes)}\n"
            
            # 샘플 데이터 (최대 3행)
            sample_data = df.head(3)
            info_str += f"- 샘플 데이터:\n{sample_data.to_string()}\n"
            
            # 숫자형 컬럼의 기본 통계
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                info_str += f"- 숫자형 컬럼 통계:\n"
                for col in numeric_cols:
                    try:
                        stats = df[col].describe()
                        info_str += f"  {col}: 범위 {stats['min']:.1f}~{stats['max']:.1f}, 평균 {stats['mean']:.1f}\n"
                    except:
                        pass
            
            info_str += "\n"
        
        return info_str

    def run(self, question):
        """
        자연어 질문 → DataFrame 쿼리 코드 생성 → 실행 → 구조화된 결과 반환
        """
        
        # DataFrame 정보 생성
        df_info = self._get_dataframe_info()
        
        # LLM 프롬프트 (강화된 한 줄 코드 제한)
        system_prompt = f"""
아래의 DataFrame 목록과 사용자 질문을 참고하여 반드시 pandas 쿼리/분석 코드만 반환하세요. 

**절대적 규칙:**
1. 설명/사과/기타 텍스트 없이 오직 실행 가능한 pandas 코드만 출력하세요
2. 반드시 한 줄 코드만 생성하세요 (세미콜론 사용 금지)
3. 변수 할당 금지, 직접 결과를 반환하는 표현식만 작성하세요
4. print() 함수 사용 금지
5. 멀티라인 코드 절대 금지

**올바른 예시:**
- df_name.describe()
- df_name.groupby('year')['value'].mean()
- df_name[df_name['year'] > 2020]
- df_name.loc[df_name['value'].idxmax()]

**잘못된 예시 (절대 사용 금지):**
- df['new_col'] = df['old_col'] * 2; df.head()  # 세미콜론 사용
- result = df.groupby('year').mean()  # 변수 할당
- print(df.head())  # print 함수
- if len(df) > 0:  # 멀티라인 코드
    return df.head()

{df_info}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        try:
            # LLM 호출
            code = self.llm.chat(messages, model=self.model).strip()
            
            # 안전 검사: 세미콜론이나 멀티라인 패턴 제거
            code = code.split(';')[0].strip()  # 첫 번째 명령만 사용
            code = code.split('\n')[0].strip()  # 첫 번째 줄만 사용
            
            # 코드 정리
            if code.startswith('```'):
                code = code.split('\n')[1] if '\n' in code else code[3:]
            if code.endswith('```'):
                code = code[:-3]
            code = code.strip()
            
            print(f"[생성된 코드] {code}")
            
            # 코드 실행을 위한 안전한 환경 구성
            safe_globals = {
                # 기본 내장 함수들
                "int": int,
                "float": float,
                "str": str,
                "len": len,
                "max": max,
                "min": min,
                "sum": sum,
                "abs": abs,
                "round": round,
                # pandas와 numpy
                "pd": pd,
                "np": np,
            }
            
            # DataFrame들을 로컬 변수로 추가
            local_vars = self.dataframes.copy()
            
            # 코드 실행
            result = eval(code, safe_globals, local_vars)
            
            # 결과 처리
            if isinstance(result, pd.DataFrame):
                # DataFrame을 JSON 직렬화 가능한 형태로 변환
                result_dict = {
                    "query_code": code,
                    "columns": result.columns.tolist(),
                    "rows": [
                        {col: self._convert_value(val) for col, val in row.items()}
                        for _, row in result.iterrows()
                    ],
                    "error": None
                }
            elif isinstance(result, pd.Series):
                # Series를 DataFrame 형태로 변환
                result_dict = {
                    "query_code": code,
                    "columns": ["index", "value"],
                    "rows": [
                        {"index": self._convert_value(idx), "value": self._convert_value(val)}
                        for idx, val in result.items()
                    ],
                    "error": None
                }
            else:
                # 스칼라 값 등
                result_dict = {
                    "query_code": code,
                    "columns": ["result"],
                    "rows": [{"result": self._convert_value(result)}],
                    "error": None
                }
            
            return result_dict
            
        except Exception as e:
            return {
                "query_code": code if 'code' in locals() else "",
                "columns": [],
                "rows": [],
                "error": str(e)
            }

    def _convert_value(self, val):
        """numpy/pandas 타입을 JSON 직렬화 가능한 타입으로 변환"""
        if pd.isna(val):
            return None
        elif isinstance(val, (np.integer, np.int64, np.int32)):
            return int(val)
        elif isinstance(val, (np.floating, np.float64, np.float32)):
            return float(val)
        elif isinstance(val, np.bool_):
            return bool(val)
        elif isinstance(val, np.ndarray):
            return val.tolist()
        else:
            return val 