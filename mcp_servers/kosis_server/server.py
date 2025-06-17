#!/usr/bin/env python3
"""
KOSIS MCP Server - 표준 MCP 프로토콜 구현 v1.0
===============================================

📋 MCP 표준 준수 사항:
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Specification v1.0                       │
│                 (Model Context Protocol)                        │
│                                                                 │
│  🔌 Transport: stdio (JSON-RPC 2.0)                             │
│     ├── Standard Input/Output 통신                              │
│     ├── JSON-RPC 메시지 형식                                     │
│     └── 비동기 메시지 처리                                        │
│                                                                 │
│  🛠️ Server Features:                                            │
│     ├── Tools: KOSIS API 호출 기능                              │
│     │   ├── fetch_statistics_data                              │
│     │   ├── search_statistics                                  │
│     │   └── list_statistics                                    │
│     │                                                          │
│     ├── Resources: 메타데이터 제공                               │
│     │   ├── statistics://metadata/{tblId}                     │
│     │   └── statistics://explanation/{statId}                 │
│     │                                                          │
│     └── Prompts: 분석 템플릿 제공                                │
│         ├── analyze_population_trend                           │
│         └── compare_economic_indicators                        │
│                                                                 │
│  🔐 Security & Trust:                                           │
│     ├── API 키 환경변수 관리                                     │
│     ├── 입력값 검증 및 오류 처리                                 │
│     └── 안전한 데이터 반환                                       │
└─────────────────────────────────────────────────────────────────┘

🎯 KOSIS Open API 연동:
- URL: https://kosis.kr/openapi
- 인증: API 키 기반 (KOSIS_OPEN_API_KEY)
- 형식: JSON 응답
- 도메인: 한국 통계청 공식 데이터

🚀 FastMCP 사용:
- Anthropic에서 개발한 MCP 서버 프레임워크
- 데코레이터 기반 간편한 도구/리소스 정의
- 자동 JSON-RPC 2.0 처리
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env 없어도 동작

# FastMCP import
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("FastMCP not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastmcp"])
    from mcp.server.fastmcp import FastMCP

# KOSIS API 함수들 import
from tools import (
    fetch_kosis_data,
    search_kosis,
    get_stat_list,
    get_stat_explanation,
    get_table_meta
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MCP 서버 생성
mcp = FastMCP("KOSIS Statistical Data Server")
mcp.description = "Korean Statistical Information Service (KOSIS) MCP Server"

# ===========================
# 🔧 도구 (Tools) 정의
# ===========================

@mcp.tool()
def fetch_statistics_data(
    orgId: str,
    tblId: str,
    startPrdDe: str = "",
    endPrdDe: str = "",
    objL1: str = "",
    objL2: str = "",
    objL3: str = "",
    itmId: str = "",
    prdSe: str = "Y"
) -> Dict[str, Any]:
    """
    KOSIS 통계자료를 조회합니다.
    
    Args:
        orgId: 기관 ID (예: "101" = 통계청)
        tblId: 통계표 ID (예: "DT_1B040A3" = 주민등록인구)
        startPrdDe: 시작 시점 (YYYY, YYYYMM, YYYYMMDD)
        endPrdDe: 종료 시점 (YYYY, YYYYMM, YYYYMMDD)
        objL1: 분류1 코드
        objL2: 분류2 코드
        objL3: 분류3 코드
        itmId: 항목 코드
        prdSe: 수록주기 (Y=연, Q=분기, M=월)
    
    Returns:
        통계 데이터 및 메타정보
    """
    try:
        result = fetch_kosis_data(
            api_key=os.getenv("KOSIS_API_KEY") or os.getenv("KOSIS_OPEN_API_KEY", ""),
            orgId=orgId,
            tblId=tblId,
            startPrdDe=startPrdDe,
            endPrdDe=endPrdDe,
            objL1=objL1,
            objL2=objL2,
            objL3=objL3,
            itmId=itmId,
            prdSe=prdSe
        )
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching statistics data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@mcp.tool()
def search_statistics(keyword: str) -> Dict[str, Any]:
    """
    KOSIS 통계를 검색합니다.
    
    Args:
        keyword: 검색 키워드 (예: "인구", "GDP", "물가지수")
    
    Returns:
        검색 결과 목록
    """
    try:
        result = search_kosis(
            api_key=os.getenv("KOSIS_API_KEY") or os.getenv("KOSIS_OPEN_API_KEY", ""),
            keyword=keyword
        )
        return {
            "success": True,
            "results": result,
            "count": len(result) if isinstance(result, list) else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error searching statistics: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@mcp.tool()
def list_statistics(
    vwCd: str = "MT_ZTITLE",
    parentListId: str = ""
) -> Dict[str, Any]:
    """
    KOSIS 통계목록을 조회합니다.
    
    Args:
        vwCd: 서비스뷰 코드
            - MT_ZTITLE: 국내통계 주제별
            - MT_OTITLE: 국내통계 기관별
            - MT_GTITLE01: e-지방지표
        parentListId: 상위 목록 ID
    
    Returns:
        통계 목록
    """
    try:
        result = get_stat_list(
            api_key=os.getenv("KOSIS_API_KEY") or os.getenv("KOSIS_OPEN_API_KEY", ""),
            vwCd=vwCd,
            parentListId=parentListId
        )
        return {
            "success": True,
            "list": result,
            "count": len(result) if isinstance(result, list) else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing statistics: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ===========================
# 📁 리소스 (Resources) 정의
# ===========================

@mcp.resource("statistics://metadata/{tblId}")
def get_statistics_metadata(tblId: str) -> str:
    """
    통계표 메타데이터를 제공합니다.
    
    Args:
        tblId: 통계표 ID
    
    Returns:
        메타데이터 JSON 문자열
    """
    try:
        # 분류 정보 조회
        classifications = get_table_meta(
            api_key=os.getenv("KOSIS_API_KEY") or os.getenv("KOSIS_OPEN_API_KEY", ""),
            tblId=tblId,
            metaType="CL"
        )
        
        # 항목 정보 조회
        items = get_table_meta(
            api_key=os.getenv("KOSIS_API_KEY") or os.getenv("KOSIS_OPEN_API_KEY", ""),
            tblId=tblId,
            metaType="ITM"
        )
        
        metadata = {
            "tableId": tblId,
            "classifications": classifications,
            "items": items,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(metadata, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        return json.dumps({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@mcp.resource("statistics://explanation/{statId}")
def get_statistics_explanation(statId: str) -> str:
    """
    통계설명자료를 제공합니다.
    
    Args:
        statId: 통계 ID
    
    Returns:
        통계 설명 JSON 문자열
    """
    try:
        explanation = get_stat_explanation(
            api_key=os.getenv("KOSIS_API_KEY") or os.getenv("KOSIS_OPEN_API_KEY", ""),
            statId=statId
        )
        
        return json.dumps(explanation, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error getting explanation: {e}")
        return json.dumps({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

# ===========================
# 💬 프롬프트 (Prompts) 정의
# ===========================

@mcp.prompt()
def analyze_population_trend(region: str = "전국", years: int = 5) -> str:
    """
    인구 변화 추이 분석을 위한 프롬프트
    
    Args:
        region: 분석 대상 지역
        years: 분석 기간 (년)
    
    Returns:
        분석 프롬프트 템플릿
    """
    current_year = datetime.now().year
    start_year = current_year - years
    
    return f"""
다음 단계에 따라 {region}의 {start_year}년부터 {current_year}년까지 인구 변화를 분석해주세요:

1. fetch_statistics_data 도구를 사용하여 주민등록인구 통계 조회
   - orgId: "101" (통계청)
   - tblId: "DT_1B040A3" (주민등록인구)
   - startPrdDe: "{start_year}"
   - endPrdDe: "{current_year}"

2. 데이터 분석
   - 연도별 인구 변화율 계산
   - 평균 증감률 산출
   - 특이사항 파악

3. 결과 요약
   - 전체 기간 인구 변화 요약
   - 주요 특징 3가지
   - 향후 전망 (선택사항)

분석 결과는 표와 함께 제시해주세요.
"""

@mcp.prompt()
def compare_economic_indicators(
    indicators: List[str] = ["GDP", "물가지수", "실업률"],
    period: str = "최근 3년"
) -> str:
    """
    주요 경제지표 비교 분석을 위한 프롬프트
    
    Args:
        indicators: 비교할 경제지표 목록
        period: 분석 기간
    
    Returns:
        비교 분석 프롬프트 템플릿
    """
    return f"""
다음 경제지표들을 {period} 동안 비교 분석해주세요: {', '.join(indicators)}

분석 단계:

1. 각 지표별 데이터 수집
   - search_statistics 도구로 관련 통계표 검색
   - fetch_statistics_data 도구로 데이터 조회

2. 지표별 분석
   - 기간 내 변화 추이
   - 최고/최저 시점
   - 변동성 분석

3. 종합 비교
   - 지표 간 상관관계
   - 경제 상황 종합 평가
   - 주요 시사점

결과는 차트와 함께 시각적으로 표현해주세요.
"""

# ===========================
# 🚀 서버 실행
# ===========================

def main():
    """MCP 서버 메인 함수"""
    # 환경 변수 확인 (.env 파일에서 KOSIS_OPEN_API_KEY로 설정됨)
    api_key = os.getenv("KOSIS_API_KEY") or os.getenv("KOSIS_OPEN_API_KEY")
    if not api_key:
        logger.warning("KOSIS_API_KEY or KOSIS_OPEN_API_KEY not set. Some features may not work.")
    else:
        logger.info("KOSIS API key found")
    
    # 서버 정보 출력
    logger.info(f"Starting {mcp.name}")
    logger.info(f"Description: {mcp.description}")
    
    # stdio로 서버 실행 (FastMCP가 내부적으로 이벤트 루프 관리)
    mcp.run()

if __name__ == "__main__":
    main() 