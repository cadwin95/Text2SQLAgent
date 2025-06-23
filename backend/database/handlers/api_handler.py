"""
API Handler Base - MindsDB inspired
외부 API를 데이터베이스처럼 취급하는 핸들러
"""

import asyncio
import time
import json
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from abc import abstractmethod
import logging

from .base_handler import (
    BaseDatabaseHandler,
    DatabaseType,
    ConnectionConfig,
    QueryResult,
    TableInfo,
    SchemaInfo,
    ConnectionStatus,
    ConnectionError,
    QueryError,
    SchemaError
)

logger = logging.getLogger(__name__)


class APIHandlerError(Exception):
    """API 핸들러 관련 에러"""
    pass


class APIEndpoint:
    """API 엔드포인트 정의"""
    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        description: str = "",
        parameters: Dict[str, Any] = None,
        required_params: List[str] = None
    ):
        self.name = name
        self.url = url
        self.method = method.upper()
        self.description = description
        self.parameters = parameters or {}
        self.required_params = required_params or []


class APITable:
    """API 응답을 테이블로 매핑"""
    def __init__(
        self,
        name: str,
        endpoint: APIEndpoint,
        columns: List[Dict[str, Any]] = None,
        data_path: str = "",  # JSON 응답에서 데이터 경로 (예: "result.data")
        transform_func: Optional[callable] = None
    ):
        self.name = name
        self.endpoint = endpoint
        self.columns = columns or []
        self.data_path = data_path
        self.transform_func = transform_func


class BaseAPIHandler(BaseDatabaseHandler):
    """
    API 핸들러 베이스 클래스
    외부 API를 데이터베이스처럼 취급
    """
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._endpoints: Dict[str, APIEndpoint] = {}
        self._tables: Dict[str, APITable] = {}
        self._base_url = ""
        self._api_key = ""
        self._headers = {}
        
    @property
    def type(self) -> DatabaseType:
        return DatabaseType.EXTERNAL_API
    
    @property
    @abstractmethod
    def api_name(self) -> str:
        """API 서비스 이름"""
        pass
    
    @property
    @abstractmethod
    def supported_operations(self) -> List[str]:
        return ["SELECT", "DESCRIBE", "SHOW"]
    
    @abstractmethod
    def _initialize_endpoints(self):
        """API 엔드포인트 및 테이블 정의 초기화"""
        pass
    
    @abstractmethod
    def _prepare_request_params(self, table_name: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """쿼리 파라미터를 API 요청 파라미터로 변환"""
        pass
    
    async def connect(self) -> bool:
        """API 연결 (세션 생성)"""
        try:
            self._set_status(ConnectionStatus.CONNECTING)
            
            # API 설정 초기화
            self._initialize_api_config()
            
            # 엔드포인트 초기화
            self._initialize_endpoints()
            
            # HTTP 세션 생성
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=timeout
            )
            
            self._set_status(ConnectionStatus.CONNECTED)
            self.logger.info(f"Connected to {self.api_name} API")
            return True
            
        except Exception as e:
            error_msg = self.format_error(e)
            self._set_status(ConnectionStatus.ERROR, error_msg)
            self.logger.error(f"{self.api_name} API connection failed: {error_msg}")
            return False
    
    async def disconnect(self) -> bool:
        """API 연결 해제"""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self._set_status(ConnectionStatus.DISCONNECTED)
            self.logger.info(f"Disconnected from {self.api_name} API")
            return True
            
        except Exception as e:
            self.logger.error(f"{self.api_name} API disconnect error: {e}")
            return False
    
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """API 연결 테스트"""
        try:
            start_time = time.time()
            
            # 테스트용 간단한 요청
            test_url = f"{self._base_url}/test" if hasattr(self, '_test_endpoint') else self._base_url
            
            async with aiohttp.ClientSession(headers=self._headers) as session:
                async with session.get(test_url) as response:
                    if response.status < 400:
                        latency = round((time.time() - start_time) * 1000, 2)
                        message = f"Connected successfully (Status: {response.status}, Latency: {latency}ms)"
                        return True, message
                    else:
                        return False, f"API returned status {response.status}"
                        
        except Exception as e:
            return False, self.format_error(e)
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> QueryResult:
        """API 쿼리 실행 (SQL-like to API 호출 변환)"""
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.api_name} API")
        
        start_time = time.time()
        
        try:
            # 쿼리 파싱 (간단한 SELECT 문만 지원)
            parsed = self._parse_query(query)
            table_name = parsed.get("table")
            
            if not table_name or table_name not in self._tables:
                raise QueryError(f"Table '{table_name}' not found")
            
            # API 호출 실행
            data = await self._execute_api_call(table_name, parsed.get("where", {}), params)
            
            # 결과 변환
            columns = [col["name"] for col in self._tables[table_name].columns]
            row_count = len(data) if isinstance(data, list) else 1
            
            execution_time = time.time() - start_time
            self._log_query(query, execution_time, True)
            
            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=row_count,
                execution_time=execution_time,
                metadata={"api_name": self.api_name, "table": table_name}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = self.format_error(e)
            self._log_query(query, execution_time, False)
            
            return QueryResult(
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
    
    async def get_tables(self, schema: Optional[str] = None) -> List[TableInfo]:
        """API 테이블 목록 조회 (엔드포인트 목록)"""
        try:
            tables = []
            for table_name, table_def in self._tables.items():
                table_info = TableInfo(
                    name=table_name,
                    schema=self.api_name,
                    type="api_endpoint",
                    comment=table_def.endpoint.description,
                    columns=table_def.columns
                )
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            raise SchemaError(f"Failed to get {self.api_name} API tables: {e}")
    
    async def get_schema(self) -> SchemaInfo:
        """API 스키마 정보 조회"""
        try:
            tables = await self.get_tables()
            
            return SchemaInfo(
                name=self.api_name,
                tables=tables,
                views=[],
                procedures=[]
            )
            
        except Exception as e:
            raise SchemaError(f"Failed to get {self.api_name} API schema: {e}")
    
    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> TableInfo:
        """특정 API 테이블 정보 조회"""
        try:
            if table_name not in self._tables:
                raise SchemaError(f"API table {table_name} not found")
            
            table_def = self._tables[table_name]
            
            return TableInfo(
                name=table_name,
                schema=self.api_name,
                type="api_endpoint",
                comment=table_def.endpoint.description,
                columns=table_def.columns
            )
            
        except Exception as e:
            raise SchemaError(f"Failed to get {self.api_name} API table info: {e}")
    
    def _initialize_api_config(self):
        """API 설정 초기화 (서브클래스에서 구현)"""
        self._base_url = self.config.host or ""
        self._api_key = self.config.password or ""
        
        if self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"
    
    def _parse_query(self, query: str) -> Dict[str, Any]:
        """간단한 SQL 쿼리 파싱"""
        # 매우 기본적인 SELECT 문 파싱
        query = query.strip().upper()
        
        if not query.startswith("SELECT"):
            raise QueryError("Only SELECT queries are supported for API calls")
        
        # FROM 절에서 테이블명 추출
        from_idx = query.find("FROM")
        if from_idx == -1:
            raise QueryError("FROM clause is required")
        
        # 테이블명 추출 (간단한 파싱)
        table_part = query[from_idx + 4:].strip()
        where_idx = table_part.find("WHERE")
        
        if where_idx != -1:
            table_name = table_part[:where_idx].strip()
            where_clause = table_part[where_idx + 5:].strip()
        else:
            table_name = table_part.strip()
            where_clause = ""
        
        return {
            "table": table_name.lower(),
            "where": self._parse_where_clause(where_clause)
        }
    
    def _parse_where_clause(self, where_clause: str) -> Dict[str, Any]:
        """WHERE 절 파싱 (매우 기본적)"""
        if not where_clause:
            return {}
        
        # 간단한 key=value 형태만 지원
        conditions = {}
        parts = where_clause.split("AND")
        
        for part in parts:
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                conditions[key] = value
        
        return conditions
    
    async def _execute_api_call(self, table_name: str, where_params: Dict[str, Any], extra_params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """실제 API 호출 실행"""
        if not self._session:
            raise APIHandlerError("API session not initialized")
        
        table_def = self._tables[table_name]
        endpoint = table_def.endpoint
        
        # 요청 파라미터 준비
        api_params = self._prepare_request_params(table_name, where_params)
        if extra_params:
            api_params.update(extra_params)
        
        # API 호출
        try:
            if endpoint.method == "GET":
                async with self._session.get(endpoint.url, params=api_params) as response:
                    response.raise_for_status()
                    result = await response.json()
            else:
                async with self._session.post(endpoint.url, json=api_params) as response:
                    response.raise_for_status()
                    result = await response.json()
            
            # 데이터 추출 및 변환
            data = self._extract_data_from_response(result, table_def)
            
            return data
            
        except aiohttp.ClientError as e:
            raise APIHandlerError(f"API request failed: {e}")
        except Exception as e:
            raise APIHandlerError(f"API call error: {e}")
    
    def _extract_data_from_response(self, response: Dict[str, Any], table_def: APITable) -> List[Dict[str, Any]]:
        """API 응답에서 데이터 추출"""
        data = response
        
        # 데이터 경로 탐색
        if table_def.data_path:
            for key in table_def.data_path.split("."):
                if key in data:
                    data = data[key]
                else:
                    return []
        
        # 변환 함수 적용
        if table_def.transform_func:
            data = table_def.transform_func(data)
        
        # 리스트가 아니면 리스트로 변환
        if not isinstance(data, list):
            data = [data]
        
        return data
    
    async def get_version(self) -> Optional[str]:
        """API 버전 조회"""
        return f"{self.api_name} API v1.0" 