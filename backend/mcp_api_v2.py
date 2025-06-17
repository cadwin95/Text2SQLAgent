# mcp_api_v2.py
# ===============
# KOSIS 공공데이터 API MCP 서버 (FastMCP 기반 - 리팩토링 버전)
# - 불필요한 DEPRECATED 함수들 제거
# - FastMCP를 활용한 깔끔한 도구/프롬프트/리소스 구조
# - 공식 명세 기반 정확한 Input/Output 형식
# - 확장 가능하고 유지보수 가능한 구조

import os
import requests
import pandas as pd
import json
import re
from dotenv import load_dotenv
from fastmcp import FastMCP

# 환경 설정
load_dotenv()

# MCP 서버 생성
mcp = FastMCP("KOSIS-API-Clean")

# API 기본 설정
BASE_URL = "https://kosis.kr/openapi/"
DEFAULT_API_KEY = os.environ.get("KOSIS_OPEN_API_KEY", "")

# =============================================================================
# 핵심 KOSIS API 도구들 (공식 명세 기반)
# =============================================================================

@mcp.tool()
def fetch_kosis_data(
    orgId: str, 
    tblId: str, 
    prdSe: str = "Y", 
    startPrdDe: str = "", 
    endPrdDe: str = "", 
    itmId: str = "", 
    objL1: str = "", 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    KOSIS 통계자료 조회 (statisticsParameterData.do)
    
    📋 Input Parameters (Official Specification):
    - orgId (필수): 기관 ID (예: "101"=통계청)
    - tblId (필수): 통계표 ID (예: "DT_1B040A3"=주민등록인구)
    - prdSe: 수록주기 (Y=연, Q=분기, M=월, D=일)
    - startPrdDe/endPrdDe: 시작/종료 시점 (YYYY, YYYYMM, YYYYMMDD)
    - itmId: 항목 ID (예: "T20"=계)
    - objL1: 분류1 코드 (예: "00"=전국)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택, 환경변수 우선)
    
    📊 Output: DataFrame 변환 가능한 JSON 구조
    
    공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0201List.do
    """
    # API 키 설정
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    # API 호출
    url = f"{BASE_URL}Param/statisticsParameterData.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "orgId": orgId,
        "tblId": tblId,
        "prdSe": prdSe,
        "format": format,
        "jsonVD": "Y"
    }
    
    # 선택적 파라미터 추가
    if itmId:
        params["itmId"] = itmId
    if objL1:
        params["objL1"] = objL1
    if startPrdDe and endPrdDe:
        params["startPrdDe"] = startPrdDe
        params["endPrdDe"] = endPrdDe
    elif not (startPrdDe or endPrdDe):
        params["newEstPrdCnt"] = "5"  # 최근 5개 시점
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # HTML 응답 체크
        if response.text.strip().startswith('<'):
            return {
                "error": "HTML 응답 반환됨 - API 키나 파라미터를 확인하세요",
                "data": [],
                "params": params
            }
        
        data = response.json()
        
        # 에러 응답 체크
        if isinstance(data, dict) and ('err' in data or 'error' in data):
            return {"error": f"API 오류: {data}", "data": [], "params": params}
        
        # 성공 응답 처리
        if isinstance(data, list):
            return {"data": data, "count": len(data), "params": params}
        elif isinstance(data, dict) and 'data' in data:
            return {"data": data['data'], "count": len(data['data']), "params": params}
        else:
            return {"data": [data] if data else [], "count": 1 if data else 0, "params": params}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"네트워크 오류: {e}", "data": [], "params": params}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 파싱 오류: {e}", "data": [], "params": params}
    except Exception as e:
        return {"error": f"예상치 못한 오류: {e}", "data": [], "params": params}

@mcp.tool()
def get_stat_list(
    vwCd: str = "MT_ZTITLE", 
    parentListId: str = "", 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    KOSIS 통계목록 조회 (statisticsList.do)
    
    📋 Input Parameters:
    - vwCd: 서비스뷰 코드
      * MT_ZTITLE: 국내통계 주제별
      * MT_OTITLE: 국내통계 기관별  
      * MT_GTITLE01: e-지방지표(주제별)
    - parentListId: 상위 목록 ID (빈 값이면 최상위)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 통계목록 JSON 배열
    
    공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0101List.do
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    url = f"{BASE_URL}statisticsList.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "vwCd": vwCd,
        "parentListId": parentListId,
        "format": format
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # JSON 속성명 수정 (KOSIS API 특성)
        text = re.sub(r'([,{])([A-Z_]+):', r'\1"\2":', response.text)
        data = json.loads(text)
        
        return {"data": data, "count": len(data) if isinstance(data, list) else 1, "params": params}
        
    except Exception as e:
        return {"error": f"통계목록 조회 오류: {e}", "data": [], "params": params}

@mcp.tool()
def get_stat_explanation(
    statId: str, 
    metaItm: str = "All", 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    KOSIS 통계설명 조회 (statisticsDetail.do)
    
    📋 Input Parameters:
    - statId: 통계조사 ID (필수)
    - metaItm: 요청 항목 (All, statsNm, writingPurps, examinPd 등)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 통계설명 JSON
    
    공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0401List.do
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": {}}
    
    url = f"{BASE_URL}statisticsDetail.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "statId": statId,
        "metaItm": metaItm,
        "format": format
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        text = re.sub(r'([,{])([A-Z_]+):', r'\1"\2":', response.text)
        data = json.loads(text)
        
        return {"data": data, "params": params}
        
    except Exception as e:
        return {"error": f"통계설명 조회 오류: {e}", "data": {}, "params": params}

# =============================================================================
# 프롬프트 (LLM 가이드)
# =============================================================================

@mcp.prompt()
def kosis_usage_guide() -> str:
    """KOSIS API 사용 가이드 및 실제 예시"""
    return """
# KOSIS API 사용 가이드

## 1. 추천 사용 패턴

### 직접 조회 (가장 안정적)
```python
# 인구 통계 조회
fetch_kosis_data(
    orgId="101",           # 통계청
    tblId="DT_1B040A3",   # 주민등록인구
    prdSe="Y",            # 연간
    startPrdDe="2020", 
    endPrdDe="2024",
    itmId="T20",          # 계(총인구)
    objL1="00"            # 전국
)
```

### 탐색적 조회
```python
# 1단계: 주제별 통계목록 조회
get_stat_list(vwCd="MT_ZTITLE", parentListId="")

# 2단계: 특정 주제 하위 통계표 조회  
get_stat_list(vwCd="MT_ZTITLE", parentListId="A")

# 3단계: 통계설명 조회
get_stat_explanation(statId="1962009")
```

## 2. 검증된 통계표 목록

### 인구/사회 (orgId="101", 통계청)
- DT_1B040A3: 주민등록인구 (추천)
- DT_1IN1502: 인구총조사
- DT_1BPA003: 장래인구추계

### 경제/노동 (orgId="101")  
- DT_1DA7001: GDP(국내총생산)
- DT_1DD0001: 소비자물가지수

## 3. 에러 처리
- API 키 오류: KOSIS_OPEN_API_KEY 환경변수 확인
- HTML 응답: 파라미터 형식 확인
- 빈 데이터: orgId, tblId 조합 확인

## 4. 프롬프트 팁
- 구체적인 orgId, tblId 명시 권장
- 시점은 YYYY 형식 사용 (2020, 2024)
- 항목은 "T20"(계), 분류는 "00"(전국) 기본값
"""

@mcp.prompt()  
def kosis_troubleshooting() -> str:
    """KOSIS API 문제 해결 가이드"""
    return """
# KOSIS API 문제 해결

## 일반적인 오류와 해결책

### 1. "HTML 응답 반환됨"
**원인**: 잘못된 API 키 또는 파라미터
**해결**: 
- KOSIS_OPEN_API_KEY 환경변수 확인
- orgId, tblId 형식 확인 (문자열)

### 2. "빈 데이터 반환"  
**원인**: 존재하지 않는 통계표 또는 조건
**해결**:
- get_stat_list로 유효한 통계표 확인
- 시점 범위 조정 (startPrdDe, endPrdDe)

### 3. "API 오류" 
**원인**: KOSIS 서버 오류 또는 제한
**해결**:
- 잠시 후 재시도
- 파라미터 단순화 (필수만 사용)

### 4. 권장 디버깅 순서
1. get_stat_list로 통계표 존재 확인
2. 기본 파라미터로 단순 조회
3. 점진적으로 조건 추가
4. 응답 구조 확인 후 DataFrame 변환

### 5. 성능 최적화
- 불필요한 필드 제외
- 시점 범위 최소화  
- 캐싱 활용 고려
"""

# =============================================================================
# 리소스 (데이터 및 설정)
# =============================================================================

@mcp.resource("kosis://schemas/population")
def population_table_schema() -> str:
    """인구 통계표 스키마 정보"""
    return json.dumps({
        "table": "DT_1B040A3",
        "name": "주민등록인구",
        "org": "통계청(101)",
        "fields": {
            "PRD_DE": "수록시점 (YYYY)",
            "C1_NM": "행정구역명",
            "ITM_NM": "항목명 (계, 남자, 여자)",
            "DT": "수치값",
            "UNIT_NM": "단위명"
        },
        "common_params": {
            "orgId": "101",
            "tblId": "DT_1B040A3", 
            "itmId": "T20",
            "objL1": "00"
        }
    }, ensure_ascii=False, indent=2)

@mcp.resource("kosis://examples/recent-population")
def recent_population_example() -> str:
    """최근 5년 인구 조회 예시"""
    return json.dumps({
        "description": "2020-2024 전국 인구수 조회",
        "tool_call": {
            "name": "fetch_kosis_data",
            "parameters": {
                "orgId": "101",
                "tblId": "DT_1B040A3",
                "prdSe": "Y",
                "startPrdDe": "2020",
                "endPrdDe": "2024",
                "itmId": "T20", 
                "objL1": "00"
            }
        },
        "expected_output": {
            "data": [
                {"PRD_DE": "2020", "DT": "51829023", "UNIT_NM": "명"},
                {"PRD_DE": "2024", "DT": "51169148", "UNIT_NM": "명"}
            ]
        }
    }, ensure_ascii=False, indent=2)

# =============================================================================
# 유틸리티 함수들
# =============================================================================

def convert_to_dataframe(kosis_result: dict) -> pd.DataFrame:
    """KOSIS API 결과를 pandas DataFrame으로 변환"""
    if "data" not in kosis_result or not kosis_result["data"]:
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(kosis_result["data"])
        # 수치값 컬럼 변환
        if "DT" in df.columns:
            df["DT"] = pd.to_numeric(df["DT"], errors='coerce')
        return df
    except Exception as e:
        print(f"DataFrame 변환 오류: {e}")
        return pd.DataFrame()

def get_verified_tables() -> dict:
    """검증된 KOSIS 통계표 목록"""
    return {
        "population": {
            "orgId": "101", "tblId": "DT_1B040A3", 
            "name": "주민등록인구", "category": "인구/사회"
        },
        "gdp": {
            "orgId": "101", "tblId": "DT_1DA7001", 
            "name": "국내총생산", "category": "경제"
        },
        "cpi": {
            "orgId": "101", "tblId": "DT_1DD0001", 
            "name": "소비자물가지수", "category": "경제"
        }
    }

# =============================================================================
# 서버 실행
# =============================================================================

if __name__ == "__main__":
    print("🚀 KOSIS API MCP Server (FastMCP 기반)")
    print(f"📊 사용 가능한 도구: fetch_kosis_data, get_stat_list, get_stat_explanation")
    print(f"📋 사용 가능한 프롬프트: kosis_usage_guide, kosis_troubleshooting")
    print(f"📁 사용 가능한 리소스: population schema, recent-population example")
    mcp.run(transport="stdio") 