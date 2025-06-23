"""
KOSIS API Handler - MindsDB inspired
한국 통계청(KOSIS) API를 데이터베이스처럼 취급하는 핸들러
"""

import os
import time
import json
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .api_handler import BaseAPIHandler, APIEndpoint, APITable
from .base_handler import DatabaseType, ConnectionConfig


class KOSISHandler(BaseAPIHandler):
    """KOSIS API 핸들러"""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        
    @property
    def type(self) -> DatabaseType:
        return DatabaseType.KOSIS_API
    
    @property
    def api_name(self) -> str:
        return "KOSIS"
    
    @property
    def supported_operations(self) -> List[str]:
        return ["SELECT", "DESCRIBE", "SHOW", "SEARCH"]
    
    def _initialize_api_config(self):
        """KOSIS API 설정 초기화"""
        self._base_url = "https://kosis.kr/openapi"
        self._api_key = self.config.password or os.getenv("KOSIS_OPEN_API_KEY", "")
        
        # KOSIS API는 Authorization 헤더 대신 파라미터로 API 키 전달
        self._headers = {
            "Content-Type": "application/json",
            "User-Agent": "Text2SQL-Agent/1.0"
        }
    
    def _initialize_endpoints(self):
        """KOSIS API 엔드포인트 및 테이블 정의"""
        
        # 1. 통계 데이터 조회 엔드포인트
        stats_data_endpoint = APIEndpoint(
            name="statistics_data",
            url=f"{self._base_url}/statisticsParameterData.do",
            method="GET",
            description="통계 데이터 조회",
            parameters={
                "method": "getList",
                "apiKey": self._api_key,
                "format": "json",
                "jsonVD": "Y",
                "userStatsId": "",
                "prdSe": "",
                "startPrdDe": "",
                "endPrdDe": "",
                "orgId": "",
                "tblId": ""
            },
            required_params=["userStatsId", "orgId", "tblId"]
        )
        
        self._endpoints["statistics_data"] = stats_data_endpoint
        self._tables["statistics_data"] = APITable(
            name="statistics_data",
            endpoint=stats_data_endpoint,
            columns=[
                {"name": "PRD_DE", "type": "string", "description": "기간"},
                {"name": "PRD_SE", "type": "string", "description": "기간구분"},
                {"name": "ITM_NM", "type": "string", "description": "항목명"},
                {"name": "ITM_ID", "type": "string", "description": "항목ID"},
                {"name": "UNIT_NM", "type": "string", "description": "단위"},
                {"name": "DT", "type": "number", "description": "값"},
                {"name": "C1", "type": "string", "description": "분류1"},
                {"name": "C1_NM", "type": "string", "description": "분류1명"},
                {"name": "C2", "type": "string", "description": "분류2"},
                {"name": "C2_NM", "type": "string", "description": "분류2명"}
            ],
            data_path="result.data",
            transform_func=self._transform_statistics_data
        )
        
        # 2. 통계 목록 조회 엔드포인트
        stats_list_endpoint = APIEndpoint(
            name="statistics_list",
            url=f"{self._base_url}/statisticsList.do",
            method="GET",
            description="통계 목록 조회",
            parameters={
                "method": "getList",
                "apiKey": self._api_key,
                "format": "json",
                "jsonVD": "Y",
                "vwCd": "MT_ZTITLE",
                "parentListId": "MT_ZTITLE",
                "orgId": "",
                "tblId": ""
            }
        )
        
        self._endpoints["statistics_list"] = stats_list_endpoint
        self._tables["statistics_list"] = APITable(
            name="statistics_list",
            endpoint=stats_list_endpoint,
            columns=[
                {"name": "LIST_ID", "type": "string", "description": "목록ID"},
                {"name": "LIST_NM", "type": "string", "description": "목록명"},
                {"name": "LIST_NM_ENG", "type": "string", "description": "목록명(영문)"},
                {"name": "GRP_LIST_ID", "type": "string", "description": "그룹목록ID"},
                {"name": "GRP_LIST_NM", "type": "string", "description": "그룹목록명"},
                {"name": "ORG_ID", "type": "string", "description": "기관ID"},
                {"name": "ORG_NM", "type": "string", "description": "기관명"},
                {"name": "TBL_ID", "type": "string", "description": "테이블ID"},
                {"name": "TBL_NM", "type": "string", "description": "테이블명"},
                {"name": "SRCH_YN", "type": "string", "description": "검색가능여부"}
            ],
            data_path="result"
        )
        
        # 3. 통계 검색 엔드포인트
        search_endpoint = APIEndpoint(
            name="statistics_search",
            url=f"{self._base_url}/statisticsSearch.do",
            method="GET", 
            description="통계 검색",
            parameters={
                "method": "getList",
                "apiKey": self._api_key,
                "format": "json",
                "jsonVD": "Y",
                "searchYN": "Y",
                "searchNm": ""
            },
            required_params=["searchNm"]
        )
        
        self._endpoints["statistics_search"] = search_endpoint
        self._tables["statistics_search"] = APITable(
            name="statistics_search",
            endpoint=search_endpoint,
            columns=[
                {"name": "TBL_ID", "type": "string", "description": "테이블ID"},
                {"name": "TBL_NM", "type": "string", "description": "테이블명"},
                {"name": "ORG_NM", "type": "string", "description": "기관명"},
                {"name": "TBL_ENG_NM", "type": "string", "description": "테이블명(영문)"},
                {"name": "CYCLE", "type": "string", "description": "주기"},
                {"name": "SURVEY_YN", "type": "string", "description": "조사여부"},
                {"name": "LOAD_DT", "type": "string", "description": "적재일시"}
            ],
            data_path="result"
        )
        
        # 4. 통계 설명 조회 엔드포인트
        stats_detail_endpoint = APIEndpoint(
            name="statistics_detail",
            url=f"{self._base_url}/statisticsDetail.do",
            method="GET",
            description="통계 설명 조회",
            parameters={
                "method": "getMeta",
                "apiKey": self._api_key,
                "format": "json",
                "jsonVD": "Y",
                "orgId": "",
                "tblId": ""
            },
            required_params=["orgId", "tblId"]
        )
        
        self._endpoints["statistics_detail"] = stats_detail_endpoint
        self._tables["statistics_detail"] = APITable(
            name="statistics_detail",
            endpoint=stats_detail_endpoint,
            columns=[
                {"name": "TBL_ID", "type": "string", "description": "테이블ID"},
                {"name": "TBL_NM", "type": "string", "description": "테이블명"},
                {"name": "ORG_NM", "type": "string", "description": "기관명"},
                {"name": "SURVEY_NM", "type": "string", "description": "조사명"},
                {"name": "SURVEY_CYCLE", "type": "string", "description": "조사주기"},
                {"name": "SURVEY_SYS", "type": "string", "description": "조사체계"},
                {"name": "SURVEY_OBJ", "type": "string", "description": "조사대상"},
                {"name": "SURVEY_MTH", "type": "string", "description": "조사방법"},
                {"name": "LOAD_DT", "type": "string", "description": "적재일시"},
                {"name": "PUB_DT", "type": "string", "description": "공표일시"}
            ],
            data_path="result"
        )
    
    def _prepare_request_params(self, table_name: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """쿼리 파라미터를 KOSIS API 요청 파라미터로 변환"""
        endpoint = self._endpoints[table_name]
        api_params = endpoint.parameters.copy()
        
        # 공통 파라미터 설정
        api_params["apiKey"] = self._api_key
        api_params["format"] = "json"
        api_params["jsonVD"] = "Y"
        
        # 테이블별 특수 파라미터 매핑
        if table_name == "statistics_data":
            # 통계 데이터 조회 파라미터 매핑
            if "userStatsId" in query_params:
                api_params["userStatsId"] = query_params["userStatsId"]
            if "orgId" in query_params:
                api_params["orgId"] = query_params["orgId"]
            if "tblId" in query_params:
                api_params["tblId"] = query_params["tblId"]
            if "startPrdDe" in query_params:
                api_params["startPrdDe"] = query_params["startPrdDe"]
            if "endPrdDe" in query_params:
                api_params["endPrdDe"] = query_params["endPrdDe"]
            if "prdSe" in query_params:
                api_params["prdSe"] = query_params["prdSe"]
                
        elif table_name == "statistics_list":
            # 통계 목록 조회 파라미터 매핑
            if "orgId" in query_params:
                api_params["orgId"] = query_params["orgId"]
            if "tblId" in query_params:
                api_params["tblId"] = query_params["tblId"]
                
        elif table_name == "statistics_search":
            # 검색 파라미터 매핑
            if "searchNm" in query_params:
                api_params["searchNm"] = query_params["searchNm"]
            api_params["searchYN"] = "Y"
            
        elif table_name == "statistics_detail":
            # 통계 설명 파라미터 매핑
            if "orgId" in query_params:
                api_params["orgId"] = query_params["orgId"]
            if "tblId" in query_params:
                api_params["tblId"] = query_params["tblId"]
        
        return api_params
    
    def _transform_statistics_data(self, data: Any) -> List[Dict[str, Any]]:
        """통계 데이터 변환"""
        if not isinstance(data, list):
            return []
        
        transformed_data = []
        for item in data:
            # KOSIS API 응답 데이터 정규화
            transformed_item = {}
            for key, value in item.items():
                # 빈 문자열을 None으로 변환
                if value == "":
                    value = None
                # 숫자 값 변환
                elif key == "DT" and value is not None:
                    try:
                        value = float(value) if '.' in str(value) else int(value)
                    except (ValueError, TypeError):
                        pass
                
                transformed_item[key] = value
            
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """KOSIS API 연결 테스트"""
        try:
            start_time = time.time()
            
            # KOSIS API 상태 확인용 간단한 요청
            test_params = {
                "method": "getList",
                "apiKey": self._api_key,
                "format": "json",
                "jsonVD": "Y",
                "vwCd": "MT_ZTITLE",
                "parentListId": "MT_ZTITLE"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._base_url}/statisticsList.do",
                    params=test_params
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            latency = round((time.time() - start_time) * 1000, 2)
                            message = f"KOSIS API connected successfully (Latency: {latency}ms)"
                            return True, message
                        else:
                            return False, "Invalid API key or access denied"
                    else:
                        return False, f"API returned status {response.status}"
                        
        except Exception as e:
            return False, self.format_error(e)
    
    async def get_version(self) -> Optional[str]:
        """KOSIS API 버전 정보"""
        return "KOSIS OpenAPI v1.0"
    
    # KOSIS 전용 헬퍼 메서드들
    async def search_statistics(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """통계 검색"""
        query = f"SELECT * FROM statistics_search WHERE searchNm = '{keyword}' LIMIT {limit}"
        result = await self.execute_query(query)
        return result.data if result.success else []
    
    async def get_statistics_by_table_id(self, org_id: str, tbl_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """테이블 ID로 통계 데이터 조회"""
        where_clause = f"orgId = '{org_id}' AND tblId = '{tbl_id}'"
        if start_date:
            where_clause += f" AND startPrdDe = '{start_date}'"
        if end_date:
            where_clause += f" AND endPrdDe = '{end_date}'"
            
        query = f"SELECT * FROM statistics_data WHERE {where_clause}"
        result = await self.execute_query(query)
        return result.data if result.success else []
    
    async def get_statistics_metadata(self, org_id: str, tbl_id: str) -> Dict[str, Any]:
        """통계 메타데이터 조회"""
        query = f"SELECT * FROM statistics_detail WHERE orgId = '{org_id}' AND tblId = '{tbl_id}'"
        result = await self.execute_query(query)
        return result.data[0] if result.success and result.data else {} 