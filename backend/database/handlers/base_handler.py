"""
Base Database Handler - MindsDB inspired architecture
다중 데이터베이스 지원을 위한 기본 핸들러 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """지원하는 데이터베이스 타입"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql" 
    MONGODB = "mongodb"
    SQLITE = "sqlite"
    REDIS = "redis"
    ORACLE = "oracle"
    MSSQL = "mssql"
    # API 핸들러들
    KOSIS_API = "kosis_api"
    EXTERNAL_API = "external_api"


class ConnectionStatus(Enum):
    """연결 상태"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


@dataclass
class ConnectionConfig:
    """연결 설정"""
    id: str
    name: str
    type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: bool = False
    connection_string: Optional[str] = None
    options: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class QueryResult:
    """쿼리 결과"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TableInfo:
    """테이블 정보"""
    name: str
    schema: Optional[str] = None
    type: str = "table"  # table, view, etc.
    columns: List[Dict[str, Any]] = None
    row_count: Optional[int] = None
    size: Optional[str] = None
    comment: Optional[str] = None
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = []


@dataclass
class SchemaInfo:
    """스키마 정보"""
    name: str
    tables: List[TableInfo] = None
    views: List[TableInfo] = None
    procedures: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.tables is None:
            self.tables = []
        if self.views is None:
            self.views = []
        if self.procedures is None:
            self.procedures = []


class BaseDatabaseHandler(ABC):
    """
    MindsDB 스타일 베이스 데이터베이스 핸들러
    모든 데이터베이스 핸들러가 상속받아야 하는 추상 클래스
    """
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.connection = None
        self.status = ConnectionStatus.DISCONNECTED
        self.last_error = None
        self.connected_at = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
    @property
    @abstractmethod
    def type(self) -> DatabaseType:
        """데이터베이스 타입 반환"""
        pass
    
    @property
    @abstractmethod
    def supported_operations(self) -> List[str]:
        """지원하는 작업 목록"""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """데이터베이스 연결"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """데이터베이스 연결 해제"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """연결 테스트"""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> QueryResult:
        """쿼리 실행"""
        pass
    
    @abstractmethod
    async def get_tables(self, schema: Optional[str] = None) -> List[TableInfo]:
        """테이블 목록 조회"""
        pass
    
    @abstractmethod
    async def get_schema(self) -> SchemaInfo:
        """스키마 정보 조회"""
        pass
    
    @abstractmethod
    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> TableInfo:
        """특정 테이블 정보 조회"""
        pass
    
    # 공통 메서드들
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.status == ConnectionStatus.CONNECTED and self.connection is not None
    
    def get_connection_info(self) -> Dict[str, Any]:
        """연결 정보 반환"""
        return {
            "id": self.config.id,
            "name": self.config.name,
            "type": self.config.type.value,
            "status": self.status.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_error": self.last_error
        }
    
    def _set_status(self, status: ConnectionStatus, error: Optional[str] = None):
        """상태 설정"""
        self.status = status
        self.last_error = error
        
        if status == ConnectionStatus.CONNECTED:
            self.connected_at = datetime.now()
        elif status == ConnectionStatus.DISCONNECTED:
            self.connected_at = None
    
    def _log_query(self, query: str, execution_time: float, success: bool):
        """쿼리 로깅"""
        log_msg = f"Query executed in {execution_time:.3f}s: {query[:100]}..."
        if success:
            self.logger.info(log_msg)
        else:
            self.logger.error(log_msg)
    
    async def execute_multiple_queries(self, queries: List[str]) -> List[QueryResult]:
        """여러 쿼리 실행"""
        results = []
        for query in queries:
            result = await self.execute_query(query)
            results.append(result)
            if not result.success:
                break  # 에러 발생시 중단
        return results
    
    async def get_database_size(self) -> Optional[str]:
        """데이터베이스 크기 조회 (서브클래스에서 구현)"""
        return None
    
    async def get_version(self) -> Optional[str]:
        """데이터베이스 버전 조회 (서브클래스에서 구현)"""
        return None
    
    def format_error(self, error: Exception) -> str:
        """에러 메시지 포맷팅"""
        return f"{self.type.value.upper()} Error: {str(error)}"
    
    def __repr__(self):
        return f"<{self.__class__.__name__}({self.config.name})>"


class DatabaseHandlerError(Exception):
    """데이터베이스 핸들러 관련 에러"""
    pass


class ConnectionError(DatabaseHandlerError):
    """연결 관련 에러"""
    pass


class QueryError(DatabaseHandlerError):
    """쿼리 관련 에러"""
    pass


class SchemaError(DatabaseHandlerError):
    """스키마 관련 에러"""
    pass 