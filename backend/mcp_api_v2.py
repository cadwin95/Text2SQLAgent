# mcp_api_v2.py
# ===============
# 🏗️ MCP SERVER (Model Context Protocol Server)
# ===============
# 역할: KOSIS 공공데이터 API와 LLM 사이의 브리지 역할을 하는 MCP 서버
# 
# 📖 MCP 아키텍처에서의 위치:
# - MCP Server: 외부 서비스(KOSIS API)를 LLM이 사용할 수 있는 도구로 변환
# - External Services: KOSIS OpenAPI (https://kosis.kr/openapi/)
# - MCP Client: integrated_api_server.py가 이 서버의 도구들을 호출
#
# 🎯 주요 기능:
# 1. KOSIS API 엔드포인트를 MCP 도구로 래핑
# 2. 표준화된 입력/출력 형식 제공
# 3. 에러 처리 및 데이터 변환
# 4. LLM을 위한 프롬프트와 리소스 제공
#
# 🔄 MCP 프로토콜 흐름:
# Client(integrated_api_server) → MCP Server(이 파일) → External API(KOSIS)
#
# 🚀 FastMCP 프레임워크 사용:
# - @mcp.tool(): LLM이 호출할 수 있는 도구 정의
# - @mcp.prompt(): LLM을 위한 가이드 프롬프트
# - @mcp.resource(): 참조 데이터 및 스키마 정보
#
# 참고: https://modelcontextprotocol.io/introduction
# FastMCP 사용법: https://python.plainenglish.io/build-your-own-mcp-server-in-an-hour-a8a1d80b54b5

import os
import requests
import pandas as pd
import json
import re
from dotenv import load_dotenv
from fastmcp import FastMCP

# 환경 설정
load_dotenv()

# MCP 서버 생성 - KOSIS API 전용 서버
mcp = FastMCP("KOSIS-API-Complete")

# API 기본 설정
BASE_URL = "https://kosis.kr/openapi/"
DEFAULT_API_KEY = os.environ.get("KOSIS_OPEN_API_KEY", "")

# =============================================================================
# 🔧 MCP TOOLS: LLM이 호출할 수 있는 KOSIS API 도구들
# =============================================================================
# 각 도구는 외부 KOSIS API를 래핑하여 LLM이 쉽게 사용할 수 있도록 변환

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
    🏢 MCP TOOL: KOSIS 통계자료 조회
    
    외부 서비스: https://kosis.kr/openapi/Param/statisticsParameterData.do
    
    📋 Input Parameters (KOSIS API 공식 명세):
    - orgId (필수): 기관 ID (예: "101"=통계청)
    - tblId (필수): 통계표 ID (예: "DT_1B040A3"=주민등록인구)
    - prdSe: 수록주기 (Y=연, Q=분기, M=월, D=일)
    - startPrdDe/endPrdDe: 시작/종료 시점 (YYYY, YYYYMM, YYYYMMDD)
    - itmId: 항목 ID (예: "T20"=계)
    - objL1: 분류1 코드 (예: "00"=전국)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택, 환경변수 우선)
    
    📊 Output: MCP Client가 사용할 수 있는 표준화된 JSON 구조
    {
        "data": [...],     # 실제 통계 데이터
        "count": int,      # 데이터 건수
        "params": {...},   # 호출에 사용된 파라미터
        "error": str       # 오류 메시지 (있는 경우)
    }
    
    🔗 공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0201List.do
    """
    # API 키 설정
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    # MCP Tool → External API 호출
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
        
        # HTML 응답 체크 (API 오류의 일반적인 형태)
        if response.text.strip().startswith('<'):
            return {
                "error": "HTML 응답 반환됨 - API 키나 파라미터를 확인하세요",
                "data": [],
                "params": params
            }
        
        data = response.json()
        
        # External API 오류 응답 처리
        if isinstance(data, dict) and ('err' in data or 'error' in data):
            return {"error": f"KOSIS API 오류: {data}", "data": [], "params": params}
        
        # 성공 응답을 MCP Client용 형식으로 변환
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
    🏢 MCP TOOL: KOSIS 통계목록 조회
    
    외부 서비스: https://kosis.kr/openapi/statisticsList.do
    
    📋 Input Parameters:
    - vwCd: 서비스뷰 코드
      * MT_ZTITLE: 국내통계 주제별
      * MT_OTITLE: 국내통계 기관별  
      * MT_GTITLE01: e-지방지표(주제별)
    - parentListId: 상위 목록 ID (빈 값이면 최상위)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 통계목록 JSON 배열
    
    🔗 공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0101List.do
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
        
        # KOSIS API 특성: JSON 속성명에 쌍따옴표 없음 → 수정 필요
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
    🏢 MCP TOOL: KOSIS 통계설명 조회
    
    외부 서비스: https://kosis.kr/openapi/statisticsDetail.do
    
    📋 Input Parameters:
    - statId: 통계조사 ID (필수)
    - metaItm: 요청 항목 (All, statsNm, writingPurps, examinPd 등)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 통계설명 JSON
    
    🔗 공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0401List.do
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

@mcp.tool()
def get_table_meta(
    tblId: str, 
    metaType: str, 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    🏢 MCP TOOL: KOSIS 통계표 메타데이터 조회
    
    외부 서비스: https://kosis.kr/openapi/statisticsList.do (메타데이터 모드)
    
    📋 Input Parameters:
    - tblId: 통계표 ID (필수)
    - metaType: 메타데이터 유형 (CL=분류, ITM=항목)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 분류/항목 코드 정보
    
    🔗 공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0101List.do
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    view_codes = {'CL': 'MT_GTITLE01', 'ITM': 'MT_GTITLE02'}
    if metaType not in view_codes:
        return {"error": "metaType은 'CL' 또는 'ITM'이어야 합니다.", "data": []}
    
    url = f"{BASE_URL}statisticsList.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "format": format,
        "jsonVD": "Y",
        "vwCd": view_codes[metaType],
        "tblId": tblId
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        text = re.sub(r'([,{])([A-Z_]+):', r'\1"\2":', response.text)
        data = json.loads(text)
        
        return {"data": data, "count": len(data) if isinstance(data, list) else 1, "params": params}
        
    except Exception as e:
        return {"error": f"메타데이터 조회 오류: {e}", "data": [], "params": params}

@mcp.tool()
def get_bigdata(
    userStatsId: str, 
    type_: str = "DSD", 
    format_: str = "sdmx", 
    version: str = "",
    api_key: str = ""
) -> dict:
    """
    🏢 MCP TOOL: KOSIS 대용량 통계자료 조회
    
    외부 서비스: https://kosis.kr/openapi/statisticsBigData.do
    
    📋 Input Parameters:
    - userStatsId: 사용자 등록 통계표 ID (필수)
    - type_: SDMX 유형 (DSD 등)
    - format_: 결과 형식 (sdmx)
    - version: 결과값 구분 (선택)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 대용량 통계자료 (SDMX 형식)
    
    🔗 공식 명세: https://kosis.kr/openapi/devGuide/devGuide_030101List.do
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    url = f"{BASE_URL}statisticsBigData.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "userStatsId": userStatsId,
        "type": type_,
        "format": format_
    }
    
    if version:
        params["version"] = version
    
    try:
        response = requests.get(url, params=params, timeout=60)  # 대용량 데이터이므로 타임아웃 증가
        response.raise_for_status()
        
        # SDMX 형식은 XML이므로 별도 처리
        if format_ == "sdmx":
            return {"data": response.text, "format": "sdmx", "params": params}
        else:
            data = response.json()
            return {"data": data, "params": params}
        
    except Exception as e:
        return {"error": f"대용량 데이터 조회 오류: {e}", "data": [], "params": params}

@mcp.tool()
def search_kosis(
    keyword: str, 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    🏢 MCP TOOL: KOSIS 통합검색
    
    외부 서비스: https://kosis.kr/openapi/statisticsSearch.do
    
    📋 Input Parameters:
    - keyword: 검색 키워드 (필수)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 검색 결과 목록
    
    🔗 공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0701List.do
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    url = f"{BASE_URL}statisticsSearch.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "searchNm": keyword,
        "format": format
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        text = re.sub(r'([,{])([A-Z_]+):', r'\1"\2":', response.text)
        data = json.loads(text)
        
        return {"data": data, "count": len(data) if isinstance(data, list) else 1, "params": params}
        
    except Exception as e:
        return {"error": f"통합검색 오류: {e}", "data": [], "params": params}

@mcp.tool()
def fetch_kosis_data_by_userStatsId(
    userStatsId: str, 
    prdSe: str = "Y", 
    startPrdDe: str = "", 
    endPrdDe: str = "", 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    🏢 MCP TOOL: 사용자 등록 통계표 기반 데이터 조회
    
    외부 서비스: https://kosis.kr/openapi/statisticsData.do
    
    📋 Input Parameters:
    - userStatsId: 사용자 등록 통계표 ID (필수)
    - prdSe: 수록주기 (Y=연, Q=분기, M=월, D=일)
    - startPrdDe/endPrdDe: 시작/종료 시점
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    📊 Output: 통계자료 JSON
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    url = f"{BASE_URL}statisticsData.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "userStatsId": userStatsId,
        "prdSe": prdSe,
        "format": format,
        "jsonVD": "Y"
    }
    
    if startPrdDe:
        params["startPrdDe"] = startPrdDe
    if endPrdDe:
        params["endPrdDe"] = endPrdDe
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        if response.text.strip().startswith('<'):
            return {
                "error": "HTML 응답 반환됨 - userStatsId나 파라미터를 확인하세요",
                "data": [],
                "params": params
            }
        
        data = response.json()
        
        if isinstance(data, list):
            return {"data": data, "count": len(data), "params": params}
        elif isinstance(data, dict) and 'data' in data:
            return {"data": data['data'], "count": len(data['data']), "params": params}
        else:
            return {"data": [data] if data else [], "count": 1 if data else 0, "params": params}
            
    except Exception as e:
        return {"error": f"사용자 통계표 조회 오류: {e}", "data": [], "params": params}

# =============================================================================
# 💬 MCP PROMPTS: LLM을 위한 사용 가이드
# =============================================================================
# MCP Client(integrated_api_server)의 LLM이 이 서버의 도구들을 효과적으로 사용할 수 있도록 돕는 프롬프트

@mcp.prompt()
def kosis_usage_guide() -> str:
    """MCP Server 사용 가이드: MCP Client의 LLM이 KOSIS 도구들을 효과적으로 사용하는 방법"""
    return """
# 🏗️ KOSIS MCP Server 사용 가이드 (Client용)

## 📡 MCP Client → Server 호출 패턴

### 1. 직접 데이터 조회 (추천)
```python
# MCP Tool 호출: fetch_kosis_data
result = mcp_tool_call("fetch_kosis_data", {
    "orgId": "101",           # 통계청
    "tblId": "DT_1B040A3",   # 주민등록인구
    "prdSe": "Y",            # 연간
    "startPrdDe": "2020", 
    "endPrdDe": "2024",
    "itmId": "T20",          # 계(총인구)
    "objL1": "00"            # 전국
})
```

### 2. 탐색적 조회
```python
# 1단계: 통계목록 조회
stats_list = mcp_tool_call("get_stat_list", {
    "vwCd": "MT_ZTITLE", 
    "parentListId": ""
})

# 2단계: 메타데이터 조회  
meta_data = mcp_tool_call("get_table_meta", {
    "tblId": "DT_1B040A3", 
    "metaType": "CL"
})

# 3단계: 실제 데이터 조회
data = mcp_tool_call("fetch_kosis_data", {...})
```

### 3. 검색 기반 조회
```python
# 키워드 검색
search_results = mcp_tool_call("search_kosis", {
    "keyword": "인구"
})

# 검색 결과에서 통계표 선택 후 데이터 조회
data = mcp_tool_call("fetch_kosis_data", {
    "orgId": search_results["data"][0]["ORG_ID"],
    "tblId": search_results["data"][0]["TBL_ID"]
})
```

## 🎯 검증된 통계표 (즉시 사용 가능)

### 인구/사회 (orgId="101", 통계청)
- DT_1B040A3: 주민등록인구 ⭐ 추천
- DT_1IN1502: 인구총조사
- DT_1BPA003: 장래인구추계

### 경제/노동 (orgId="101")  
- DT_1DA7001: GDP(국내총생산)
- DT_1DD0001: 소비자물가지수

## ⚠️ MCP Client 에러 처리

### 일반적인 응답 형식
```json
{
    "data": [...],        // 성공 시 실제 데이터
    "count": 100,         // 데이터 건수
    "params": {...},      // 호출 파라미터
    "error": "오류메시지"  // 실패 시 오류 내용
}
```

### 에러 대응 전략
1. **"HTML 응답 반환됨"** → API 키나 파라미터 확인
2. **"빈 데이터"** → 다른 통계표나 시점 범위 시도
3. **"API 오류"** → 잠시 후 재시도 또는 대안 도구 사용

## 💡 MCP Client 팁
- 구체적인 orgId, tblId 명시 권장
- 시점은 YYYY 형식 사용 (2020, 2024)
- 항목은 "T20"(계), 분류는 "00"(전국) 기본값
- 검색으로 시작해서 점진적으로 좁혀나가기
"""

@mcp.prompt()  
def kosis_troubleshooting() -> str:
    """MCP Server 문제 해결 가이드: Client가 Server 호출 시 발생하는 문제들의 해결 방법"""
    return """
# 🔧 KOSIS MCP Server 문제 해결 (Client용)

## 🚨 일반적인 MCP Tool 호출 오류

### 1. "KOSIS_OPEN_API_KEY가 설정되지 않았습니다"
**원인**: MCP Server에 API 키가 없음
**해결**: 
- MCP Server 환경변수 확인: `KOSIS_OPEN_API_KEY`
- tool 호출 시 api_key 파라미터 직접 전달

### 2. "HTML 응답 반환됨"
**원인**: KOSIS API가 HTML 오류 페이지 반환
**해결**: 
- orgId, tblId 파라미터 형식 확인 (문자열)
- API 키 유효성 검사
- 검증된 통계표 사용

### 3. "빈 데이터 반환"  
**원인**: 존재하지 않는 통계표 또는 조건
**해결**:
- get_stat_list로 유효한 통계표 먼저 확인
- 시점 범위 조정 (startPrdDe, endPrdDe)
- 검증된 통계표 목록 사용

## 🔄 권장 디버깅 순서 (MCP Client용)

1. **search_kosis**로 키워드 검색
2. **get_stat_list**로 통계표 존재 확인
3. **get_table_meta**로 메타데이터 확인
4. **fetch_kosis_data**로 기본 파라미터로 단순 조회
5. 점진적으로 조건 추가
6. 응답 구조 확인 후 DataFrame 변환

## ⚡ 성능 최적화 (MCP Client 권장사항)

- 불필요한 필드 제외
- 시점 범위 최소화  
- 대용량 데이터는 get_bigdata 사용
- 결과 캐싱 활용 고려

## 🔗 MCP 프로토콜 레벨 디버깅

```python
# MCP Tool 호출 결과 체크
result = mcp_tool_call("fetch_kosis_data", params)

if result.get("error"):
    # 오류 처리 로직
    print(f"MCP Tool 오류: {result['error']}")
    # 대안 전략 실행
else:
    # 성공 처리
    data = result["data"]
    count = result["count"]
```
"""

# =============================================================================
# 📚 MCP RESOURCES: 참조 데이터 및 스키마 정보
# =============================================================================
# MCP Client가 참조할 수 있는 정적 정보 및 스키마

@mcp.resource("kosis://schemas/population")
def population_table_schema() -> str:
    """인구 통계표 스키마 정보 - MCP Client 참조용"""
    return json.dumps({
        "mcp_server": "KOSIS-API-Complete",
        "external_service": "KOSIS OpenAPI",
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
        "mcp_tool_params": {
            "orgId": "101",
            "tblId": "DT_1B040A3", 
            "itmId": "T20",
            "objL1": "00"
        }
    }, ensure_ascii=False, indent=2)

@mcp.resource("kosis://verified-tables")
def verified_tables_list() -> str:
    """검증된 KOSIS 통계표 목록 - MCP Client가 안전하게 사용할 수 있는 테이블들"""
    return json.dumps({
        "mcp_server_info": {
            "name": "KOSIS-API-Complete",
            "external_service": "KOSIS OpenAPI (https://kosis.kr)",
            "protocol": "Model Context Protocol (MCP)"
        },
        "verified_tables": {
            "population": {
                "orgId": "101", "tblId": "DT_1B040A3", 
                "name": "주민등록인구", "category": "인구/사회",
                "mcp_tool": "fetch_kosis_data",
                "reliability": "high"
            },
            "gdp": {
                "orgId": "101", "tblId": "DT_1DA7001", 
                "name": "국내총생산", "category": "경제",
                "mcp_tool": "fetch_kosis_data",
                "reliability": "medium"
            },
            "cpi": {
                "orgId": "101", "tblId": "DT_1DD0001", 
                "name": "소비자물가지수", "category": "경제",
                "mcp_tool": "fetch_kosis_data",
                "reliability": "medium"
            },
            "employment": {
                "orgId": "101", "tblId": "DT_1DA7002",
                "name": "고용률", "category": "노동",
                "mcp_tool": "fetch_kosis_data",
                "reliability": "low"
            }
        }
    }, ensure_ascii=False, indent=2)

@mcp.resource("kosis://api-endpoints")
def api_endpoints_info() -> str:
    """KOSIS API 엔드포인트 → MCP Tool 매핑 정보"""
    return json.dumps({
        "mcp_server_architecture": {
            "client": "integrated_api_server.py (MCP Client)",
            "server": "mcp_api_v2.py (MCP Server)",
            "external_service": "KOSIS OpenAPI"
        },
        "tool_mappings": {
            "statisticsList.do": {
                "purpose": "통계목록 조회",
                "mcp_tool": "get_stat_list",
                "external_api": "https://kosis.kr/openapi/statisticsList.do",
                "guide": "https://kosis.kr/openapi/devGuide/devGuide_0101List.do"
            },
            "statisticsParameterData.do": {
                "purpose": "통계자료 조회",
                "mcp_tool": "fetch_kosis_data", 
                "external_api": "https://kosis.kr/openapi/Param/statisticsParameterData.do",
                "guide": "https://kosis.kr/openapi/devGuide/devGuide_0201List.do"
            },
            "statisticsDetail.do": {
                "purpose": "통계설명 조회",
                "mcp_tool": "get_stat_explanation",
                "external_api": "https://kosis.kr/openapi/statisticsDetail.do",
                "guide": "https://kosis.kr/openapi/devGuide/devGuide_0401List.do"
            },
            "statisticsBigData.do": {
                "purpose": "대용량 통계자료 조회",
                "mcp_tool": "get_bigdata",
                "external_api": "https://kosis.kr/openapi/statisticsBigData.do",
                "guide": "https://kosis.kr/openapi/devGuide/devGuide_030101List.do"
            },
            "statisticsSearch.do": {
                "purpose": "통합검색",
                "mcp_tool": "search_kosis",
                "external_api": "https://kosis.kr/openapi/statisticsSearch.do",
                "guide": "https://kosis.kr/openapi/devGuide/devGuide_0701List.do"
            },
            "statisticsData.do": {
                "purpose": "사용자 등록 통계표 조회",
                "mcp_tool": "fetch_kosis_data_by_userStatsId",
                "external_api": "https://kosis.kr/openapi/statisticsData.do",
                "guide": "https://kosis.kr/openapi/devGuide/"
            }
        }
    }, ensure_ascii=False, indent=2)

# =============================================================================
# 🛠️ MCP Server 유틸리티 함수들
# =============================================================================
# MCP Tools에서 공통으로 사용되는 헬퍼 함수들

def convert_to_dataframe(kosis_result: dict) -> pd.DataFrame:
    """MCP Tool 결과를 pandas DataFrame으로 변환 (MCP Client에서 사용)"""
    if "data" not in kosis_result or not kosis_result["data"]:
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(kosis_result["data"])
        # 수치값 컬럼 변환
        if "DT" in df.columns:
            df["DT"] = pd.to_numeric(df["DT"], errors='coerce')
        return df
    except Exception as e:
        print(f"[MCP Server] DataFrame 변환 오류: {e}")
        return pd.DataFrame()

def get_verified_tables() -> dict:
    """검증된 KOSIS 통계표 목록 (MCP Server 내부용)"""
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
        },
        "employment": {
            "orgId": "101", "tblId": "DT_1DA7002",
            "name": "고용률", "category": "노동"
        }
    }

def make_api_request(endpoint: str, params: dict) -> dict:
    """공통 KOSIS API 요청 함수 (MCP Tools에서 내부 사용)"""
    url = BASE_URL + endpoint
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # JSON 속성명 수정 (KOSIS API 특성)
        text = re.sub(r'([,{])([A-Z_]+):', r'\1"\2":', response.text)
        data = json.loads(text)
        
        return {"data": data, "params": params}
        
    except Exception as e:
        return {"error": f"API 요청 오류: {e}", "data": [], "params": params}

# =============================================================================
# 🚀 MCP Server 실행부
# =============================================================================
# 이 서버는 독립적으로 실행되며, MCP Client(integrated_api_server)가 연결하여 사용

if __name__ == "__main__":
    print("🏗️ KOSIS MCP Server 시작 중...")
    print("📡 MCP 프로토콜로 KOSIS API 서비스 제공")
    print("🔗 Client 연결 대기: integrated_api_server.py")
    print("🌐 External Service: KOSIS OpenAPI (https://kosis.kr)")
    print("\n🔧 환경 변수 확인:")
    print(f"- KOSIS_OPEN_API_KEY: {'✅ 설정됨' if DEFAULT_API_KEY else '❌ 미설정'}")
    print("\n🛠️ 제공 MCP Tools:")
    print("- fetch_kosis_data (통계자료 조회)")
    print("- get_stat_list (통계목록 조회)")
    print("- get_stat_explanation (통계설명 조회)")
    print("- get_table_meta (메타데이터 조회)")
    print("- get_bigdata (대용량 데이터 조회)")
    print("- search_kosis (통합검색)")
    print("- fetch_kosis_data_by_userStatsId (사용자 등록 통계표 조회)")
    
    # FastMCP 서버 실행 (MCP 프로토콜 통신)
    mcp.run() 