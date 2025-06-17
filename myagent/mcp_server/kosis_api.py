#!/usr/bin/env python3
"""
🏗️ KOSIS MCP SERVER (독립 실행형) - 완전 개선판
==================================================
역할: KOSIS OpenAPI를 MCP 프로토콜 도구로 변환하는 독립 서버

📖 사용법:
1. 독립 실행: python kosis_api.py
2. Config 연동: mcp_config.json에서 참조
3. MCP Client와 표준 프로토콜로 통신

🔧 제공 도구:
- fetch_kosis_data: 통계자료 조회 (statisticsParameterData.do)
- fetch_kosis_data_by_userStatsId: 사용자 등록 통계표 기반 데이터 조회 (statisticsData.do)
- get_stat_list: 통계목록 탐색 (statisticsList.do)
- get_stat_explanation: 통계설명 조회 (statisticsDetail.do)
- get_table_meta: 통계표 메타데이터 조회 (통계표설명)
- get_bigdata: 대용량 통계자료 조회 (statisticsBigData.do)
- search_kosis: 통합검색 (statisticsSearch.do)

🌐 외부 서비스: KOSIS OpenAPI (https://kosis.kr)
📋 프로토콜: Model Context Protocol (MCP)
"""

import os
import requests
import pandas as pd
import json
import re
from dotenv import load_dotenv
from fastmcp import FastMCP

# 환경 설정
load_dotenv()

# MCP 서버 생성 - KOSIS 전용
mcp = FastMCP("KOSIS-Statistics-API")

# API 기본 설정
BASE_URL = "https://kosis.kr/openapi/"
DEFAULT_API_KEY = os.environ.get("KOSIS_OPEN_API_KEY", "")

# =============================================================================
# 🔧 MCP TOOLS: KOSIS API 래핑 도구들
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
    📊 KOSIS 통계자료 조회 (statisticsParameterData.do)
    
    Parameters:
    - orgId (필수): 기관 ID (예: "101"=통계청)
    - tblId (필수): 통계표 ID (예: "DT_1B040A3"=주민등록인구)
    - prdSe: 수록주기 (Y=연, Q=분기, M=월, D=일)
    - startPrdDe/endPrdDe: 시작/종료 시점 (YYYY, YYYYMM, YYYYMMDD)
    - itmId: 항목 ID (예: "T20"=계)
    - objL1: 분류1 코드 (예: "00"=전국)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택, 환경변수 우선)
    
    Returns:
    - MCP 표준 응답 형식의 통계 데이터
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
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
                "error": "HTML 응답 - API 키나 파라미터를 확인하세요",
                "data": [],
                "mcp_server": "KOSIS-Statistics-API"
            }
        
        data = response.json()
        
        if isinstance(data, dict) and ('err' in data or 'error' in data):
            return {"error": f"KOSIS API 오류: {data}", "data": []}
        
        # MCP 표준 응답 형식
        result_data = data if isinstance(data, list) else [data] if data else []
        return {
            "data": result_data,
            "count": len(result_data),
            "mcp_server": "KOSIS-Statistics-API",
            "external_api": "KOSIS statisticsParameterData.do",
            "params": params
        }
            
    except Exception as e:
        return {
            "error": f"MCP Server 오류: {e}", 
            "data": [], 
            "mcp_server": "KOSIS-Statistics-API"
        }

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
    📊 사용자 등록 통계표 기반 데이터 조회 (statisticsData.do)
    
    Parameters:
    - userStatsId (필수): 사용자 등록 통계표 ID
    - prdSe: 수록주기 (Y=연, Q=분기, M=월, D=일)
    - startPrdDe/endPrdDe: 시작/종료 시점
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    Returns:
    - 통계자료 JSON
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
        "format": format
    }
    
    # 시점 설정
    if startPrdDe and endPrdDe:
        params["startPrdDe"] = startPrdDe
        params["endPrdDe"] = endPrdDe
    else:
        params["newEstPrdCnt"] = "5"  # 최근 5개 시점
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, dict) and ('err' in data or 'error' in data):
            return {"error": f"KOSIS API 오류: {data}", "data": []}
        
        result_data = data if isinstance(data, list) else [data] if data else []
        return {
            "data": result_data,
            "count": len(result_data),
            "mcp_server": "KOSIS-Statistics-API",
            "external_api": "KOSIS statisticsData.do",
            "params": params
        }
            
    except Exception as e:
        return {
            "error": f"사용자 통계표 조회 오류: {e}", 
            "data": [], 
            "mcp_server": "KOSIS-Statistics-API"
        }

@mcp.tool()
def get_stat_list(
    vwCd: str = "MT_ZTITLE", 
    parentListId: str = "", 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    📋 KOSIS 통계목록 조회 (statisticsList.do)
    
    Parameters:
    - vwCd: 서비스뷰 코드
      * MT_ZTITLE: 국내통계 주제별
      * MT_OTITLE: 국내통계 기관별  
      * MT_GTITLE01: e-지방지표(주제별)
    - parentListId: 상위 목록ID (빈 값이면 최상위)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    Returns:
    - 통계목록 JSON 배열
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
        
        # JSON 속성명 수정 (KOSIS 특성)
        text = re.sub(r'([,{])([A-Z_]+):', r'\1"\2":', response.text)
        data = json.loads(text)
        
        return {
            "data": data, 
            "count": len(data) if isinstance(data, list) else 1,
            "mcp_server": "KOSIS-Statistics-API",
            "external_api": "KOSIS statisticsList.do"
        }
        
    except Exception as e:
        return {"error": f"통계목록 조회 오류: {e}", "data": []}

@mcp.tool()
def get_stat_explanation(
    statId: str,
    metaItm: str = "All",
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    📖 KOSIS 통계설명 조회 (statisticsDetail.do)
    
    Parameters:
    - statId: 통계조사 ID (필수)
    - metaItm: 요청 항목 (All, statsNm, writingPurps, examinPd 등)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    Returns:
    - 통계설명 JSON
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
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
        
        data = response.json()
        
        if isinstance(data, dict) and ('err' in data or 'error' in data):
            return {"error": f"KOSIS API 오류: {data}", "data": []}
        
        result_data = data if isinstance(data, list) else [data] if data else []
        return {
            "data": result_data,
            "count": len(result_data),
            "mcp_server": "KOSIS-Statistics-API",
            "external_api": "KOSIS statisticsDetail.do",
            "params": params
        }
            
    except Exception as e:
        return {
            "error": f"통계설명 조회 오류: {e}", 
            "data": [], 
            "mcp_server": "KOSIS-Statistics-API"
        }

@mcp.tool()
def get_table_meta(
    tblId: str, 
    metaType: str, 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    📋 KOSIS 통계표 메타데이터 조회 (분류/항목 코드)
    
    Parameters:
    - tblId: 통계표 ID (필수)
    - metaType: 메타데이터 유형 (CL=분류, ITM=항목)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    Returns:
    - 분류/항목 코드 정보
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    if not api_key:
        return {"error": "KOSIS_OPEN_API_KEY가 설정되지 않았습니다.", "data": []}
    
    url = f"{BASE_URL}statisticsDetail.do"
    params = {
        "method": "getMeta",
        "apiKey": api_key,
        "tblId": tblId,
        "type": metaType,
        "format": format
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, dict) and ('err' in data or 'error' in data):
            return {"error": f"KOSIS API 오류: {data}", "data": []}
        
        result_data = data if isinstance(data, list) else [data] if data else []
        return {
            "data": result_data,
            "count": len(result_data),
            "mcp_server": "KOSIS-Statistics-API",
            "external_api": "KOSIS getMeta",
            "params": params
        }
            
    except Exception as e:
        return {
            "error": f"메타데이터 조회 오류: {e}", 
            "data": [], 
            "mcp_server": "KOSIS-Statistics-API"
        }

@mcp.tool()
def get_bigdata(
    userStatsId: str,
    type_: str = "DSD",
    format_: str = "sdmx",
    version: str = "",
    api_key: str = ""
) -> dict:
    """
    💾 KOSIS 대용량 통계자료 조회 (statisticsBigData.do)
    
    Parameters:
    - userStatsId: 사용자 등록 통계표 ID (필수)
    - type_: SDMX 유형 (DSD 등)
    - format_: 결과 형식 (sdmx)
    - version: 결과값 구분 (선택)
    - api_key: KOSIS API 키 (선택)
    
    Returns:
    - 대용량 통계자료 (SDMX 형식)
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
        response = requests.get(url, params=params, timeout=60)  # 대용량이므로 타임아웃 연장
        response.raise_for_status()
        
        # SDMX 형식 응답 처리
        if format_ == "sdmx":
            return {
                "data": response.text,  # SDMX XML 텍스트
                "format": "sdmx_xml",
                "mcp_server": "KOSIS-Statistics-API",
                "external_api": "KOSIS statisticsBigData.do",
                "params": params
            }
        else:
            data = response.json()
            result_data = data if isinstance(data, list) else [data] if data else []
            return {
                "data": result_data,
                "count": len(result_data),
                "mcp_server": "KOSIS-Statistics-API",
                "external_api": "KOSIS statisticsBigData.do",
                "params": params
            }
            
    except Exception as e:
        return {
            "error": f"대용량 통계자료 조회 오류: {e}", 
            "data": [], 
            "mcp_server": "KOSIS-Statistics-API"
        }

@mcp.tool()
def search_kosis(
    keyword: str, 
    format: str = "json",
    api_key: str = ""
) -> dict:
    """
    🔍 KOSIS 통합검색 (statisticsSearch.do)
    
    Parameters:
    - keyword: 검색 키워드 (필수)
    - format: 결과 형식 (json)
    - api_key: KOSIS API 키 (선택)
    
    Returns:
    - 검색 결과 목록
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
        
        data = response.json()
        
        if isinstance(data, dict) and ('err' in data or 'error' in data):
            return {"error": f"KOSIS API 오류: {data}", "data": []}
        
        result_data = data if isinstance(data, list) else [data] if data else []
        return {
            "data": result_data,
            "count": len(result_data),
            "mcp_server": "KOSIS-Statistics-API",
            "external_api": "KOSIS statisticsSearch.do",
            "params": params
        }
            
    except Exception as e:
        return {
            "error": f"통합검색 오류: {e}", 
            "data": [], 
            "mcp_server": "KOSIS-Statistics-API"
        }

# =============================================================================
# 📋 MCP PROMPTS: 사용법 가이드
# =============================================================================

@mcp.prompt()
def kosis_usage_guide() -> str:
    """KOSIS MCP 서버 사용법 가이드"""
    return """
🏢 KOSIS MCP 서버 사용법 가이드
============================

🔧 제공 도구들:

1️⃣ fetch_kosis_data - 통계자료 직접 조회
   • orgId, tblId 필수
   • 예시: orgId="101", tblId="DT_1B040A3"

2️⃣ fetch_kosis_data_by_userStatsId - 사용자 등록 통계표 조회
   • userStatsId 필수
   • 사전 등록된 통계표 ID 필요

3️⃣ get_stat_list - 통계목록 탐색
   • vwCd: MT_ZTITLE(주제별), MT_OTITLE(기관별)
   • 계층적 탐색 가능

4️⃣ get_stat_explanation - 통계설명 조회
   • statId 필수
   • 통계조사 상세 정보 제공

5️⃣ get_table_meta - 통계표 메타데이터
   • tblId, metaType(CL/ITM) 필수
   • 분류/항목 코드 정보

6️⃣ get_bigdata - 대용량 통계자료 조회
   • userStatsId 필수
   • SDMX 형식 지원

7️⃣ search_kosis - 통합검색
   • keyword 필수
   • 전체 KOSIS 검색

🔑 API 키 설정:
환경변수 KOSIS_OPEN_API_KEY 설정 또는 api_key 파라미터 사용

📊 주요 기관 코드:
- 101: 통계청
- 145: 행정안전부  
- 327: 국토교통부

📋 수록주기 코드:
- Y: 연간, Q: 분기, M: 월간, D: 일간

🎯 사용 팁:
1. get_stat_list로 통계표 탐색
2. get_table_meta로 메타데이터 확인
3. fetch_kosis_data로 실제 데이터 조회
4. search_kosis로 키워드 검색
"""

# =============================================================================
# 📊 MCP RESOURCES: 검증된 통계표 목록
# =============================================================================

@mcp.resource("kosis://verified-tables")
def verified_tables() -> str:
    """검증된 KOSIS 통계표 목록 (리소스)"""
    return """
🏢 검증된 KOSIS 통계표 목록
=========================

📊 인구/사회:
• DT_1B040A3: 주민등록인구 (orgId=101)
• DT_1B04005: 인구이동 (orgId=101)
• DT_1YL20631: 혼인/이혼 (orgId=101)

💰 경제/금융:
• DT_1C8015: 소비자물가지수 (orgId=101)
• DT_1C8014: 생산자물가지수 (orgId=101)
• DT_1DA7002: GDP 지출 (orgId=101)

🏠 주택/부동산:
• DT_1YL20171: 주택매매가격지수 (orgId=327)
• DT_1YL12853: 아파트매매 실거래가 (orgId=327)

🏢 고용/노동:
• DT_1DA7442: 경제활동인구 (orgId=101)
• DT_1DA7443: 취업자수 (orgId=101)

🏥 보건/복지:
• DT_1B34E01: 사망원인통계 (orgId=101)
• DT_1C17171: 의료기관 현황 (orgId=117)

🎯 사용법:
fetch_kosis_data(orgId="101", tblId="DT_1B040A3")
"""

# =============================================================================
# 🚀 서버 실행부
# =============================================================================

if __name__ == "__main__":
    print("🏢 KOSIS MCP 서버 시작 중...")
    print(f"📊 제공 도구: 7개 (fetch_kosis_data, get_stat_list, search_kosis 등)")
    print(f"🔑 API 키 설정: {'✅' if DEFAULT_API_KEY else '❌ KOSIS_OPEN_API_KEY 환경변수 설정 필요'}")
    print("🌐 포트: stdio (MCP 표준)")
    
    # MCP 서버 실행
    mcp.run() 