"""
KOSIS API 도구 함수들
====================
MCP 서버에서 사용할 KOSIS API 호출 함수들
"""

import os
import requests
import pandas as pd
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# KOSIS API 기본 URL
BASE_URL = "https://kosis.kr/openapi"

def _make_api_request(endpoint: str, params: Dict[str, str]) -> Any:
    """
    KOSIS API 요청 헬퍼 함수
    
    Args:
        endpoint: API 엔드포인트
        params: 요청 파라미터
    
    Returns:
        API 응답 (JSON 파싱됨)
    """
    # API 키 설정
    if "apiKey" not in params:
        params["apiKey"] = os.getenv("KOSIS_API_KEY", "")
    
    # 기본 파라미터
    params["format"] = "json"
    params["jsonVD"] = "Y"
    
    # URL 구성
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # JSON 파싱
        data = response.json()
        
        # 오류 체크
        if "err" in data:
            raise Exception(f"API Error: {data['err']}")
        
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        raise

def fetch_kosis_data(
    api_key: str,
    orgId: str,
    tblId: str,
    startPrdDe: str = "",
    endPrdDe: str = "",
    objL1: str = "",
    objL2: str = "",
    objL3: str = "",
    itmId: str = "",
    prdSe: str = "Y",
    newEstPrdCnt: str = "1",
    loadGubun: str = "2"
) -> pd.DataFrame:
    """
    KOSIS 통계자료 조회 (statisticsParameterData.do)
    
    공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0201List.do
    
    Args:
        api_key: KOSIS API 키
        orgId: 기관 ID (필수, 예: "101"=통계청)
        tblId: 통계표 ID (필수, 예: "DT_1B040A3"=주민등록인구)
        startPrdDe: 시작 시점 (YYYY, YYYYMM, YYYYMMDD)
        endPrdDe: 종료 시점
        objL1~3: 분류 코드
        itmId: 항목 코드
        prdSe: 수록주기 (Y=연, Q=분기, M=월, D=일)
        newEstPrdCnt: 최근 수록 시점
        loadGubun: 전체/증감/증감률 (1/2/3)
    
    Returns:
        pd.DataFrame: 통계 데이터
    """
    params = {
        "method": "getList",
        "apiKey": api_key,
        "orgId": orgId,
        "tblId": tblId,
        "prdSe": prdSe,
        "newEstPrdCnt": newEstPrdCnt,
        "loadGubun": loadGubun
    }
    
    # 선택적 파라미터 추가
    if startPrdDe:
        params["startPrdDe"] = startPrdDe
    if endPrdDe:
        params["endPrdDe"] = endPrdDe
    if objL1:
        params["objL1"] = objL1
    if objL2:
        params["objL2"] = objL2
    if objL3:
        params["objL3"] = objL3
    if itmId:
        params["itmId"] = itmId
    
    try:
        data = _make_api_request("statisticsParameterData.do", params)
        
        # DataFrame 변환
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            logger.info(f"Successfully fetched {len(df)} rows from KOSIS")
            return df
        else:
            logger.warning("No data returned from KOSIS")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error in fetch_kosis_data: {e}")
        return pd.DataFrame()

def search_kosis(api_key: str, keyword: str) -> List[Dict[str, Any]]:
    """
    KOSIS 통합검색 (statisticsSearch.do)
    
    공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0701List.do
    
    Args:
        api_key: KOSIS API 키
        keyword: 검색 키워드
    
    Returns:
        List[Dict]: 검색 결과 목록
    """
    params = {
        "method": "getList",
        "apiKey": api_key,
        "searchNm": keyword
    }
    
    try:
        data = _make_api_request("statisticsSearch.do", params)
        
        if isinstance(data, list):
            logger.info(f"Found {len(data)} results for '{keyword}'")
            return data
        else:
            return []
    except Exception as e:
        logger.error(f"Error in search_kosis: {e}")
        return []

def get_stat_list(
    api_key: str,
    vwCd: str = "MT_ZTITLE",
    parentListId: str = ""
) -> List[Dict[str, Any]]:
    """
    KOSIS 통계목록 조회 (statisticsList.do)
    
    공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0101List.do
    
    Args:
        api_key: KOSIS API 키
        vwCd: 서비스뷰 코드
            - MT_ZTITLE: 국내통계 주제별
            - MT_OTITLE: 국내통계 기관별
            - MT_GTITLE01: e-지방지표(주제별)
        parentListId: 상위 목록 ID
    
    Returns:
        List[Dict]: 통계 목록
    """
    params = {
        "method": "getList",
        "apiKey": api_key,
        "vwCd": vwCd
    }
    
    if parentListId:
        params["parentListId"] = parentListId
    
    try:
        data = _make_api_request("statisticsList.do", params)
        
        if isinstance(data, list):
            logger.info(f"Retrieved {len(data)} statistics from list")
            return data
        else:
            return []
    except Exception as e:
        logger.error(f"Error in get_stat_list: {e}")
        return []

def get_stat_explanation(
    api_key: str,
    statId: str,
    metaItm: str = "All"
) -> Dict[str, Any]:
    """
    KOSIS 통계설명 조회 (statisticsDetail.do)
    
    공식 명세: https://kosis.kr/openapi/devGuide/devGuide_0401List.do
    
    Args:
        api_key: KOSIS API 키
        statId: 통계조사 ID
        metaItm: 요청 항목 (All, statsNm, writingPurps 등)
    
    Returns:
        Dict: 통계 설명 정보
    """
    params = {
        "method": "getDetail",
        "apiKey": api_key,
        "statId": statId,
        "metaItm": metaItm
    }
    
    try:
        data = _make_api_request("statisticsDetail.do", params)
        
        if isinstance(data, dict):
            logger.info(f"Retrieved explanation for stat ID: {statId}")
            return data
        else:
            return {}
    except Exception as e:
        logger.error(f"Error in get_stat_explanation: {e}")
        return {}

def get_table_meta(
    api_key: str,
    tblId: str,
    metaType: str
) -> List[Dict[str, Any]]:
    """
    KOSIS 통계표 메타데이터 조회 (분류/항목 코드)
    
    Args:
        api_key: KOSIS API 키
        tblId: 통계표 ID
        metaType: 메타데이터 유형 (CL=분류, ITM=항목)
    
    Returns:
        List[Dict]: 메타데이터 목록
    """
    # 통계표 설명 API 사용 (실제로는 별도 API가 있을 수 있음)
    params = {
        "method": "getMeta",
        "apiKey": api_key,
        "tblId": tblId,
        "type": metaType
    }
    
    try:
        # 임시로 빈 리스트 반환 (실제 API 엔드포인트 확인 필요)
        logger.warning(f"Table metadata API not fully implemented for {tblId}")
        return []
    except Exception as e:
        logger.error(f"Error in get_table_meta: {e}")
        return [] 