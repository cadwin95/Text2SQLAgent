"""
Database Handler Factory - MindsDB inspired
다중 데이터베이스 핸들러 팩토리 및 레지스트리
"""

from typing import Dict, Type, Optional, List
import importlib
import logging

from .base_handler import (
    BaseDatabaseHandler, 
    DatabaseType, 
    ConnectionConfig,
    DatabaseHandlerError
)

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """핸들러 레지스트리 - MindsDB 스타일"""
    
    def __init__(self):
        self._handlers: Dict[DatabaseType, Type[BaseDatabaseHandler]] = {}
        self._handler_modules: Dict[DatabaseType, str] = {
            DatabaseType.MYSQL: 'backend.database.handlers.mysql_handler',
            DatabaseType.POSTGRESQL: 'backend.database.handlers.postgresql_handler', 
            DatabaseType.MONGODB: 'backend.database.handlers.mongodb_handler',
            DatabaseType.SQLITE: 'backend.database.handlers.sqlite_handler',
            DatabaseType.REDIS: 'backend.database.handlers.redis_handler',
            DatabaseType.ORACLE: 'backend.database.handlers.oracle_handler',
            DatabaseType.MSSQL: 'backend.database.handlers.mssql_handler',
            # API 핸들러들
            DatabaseType.KOSIS_API: 'backend.database.handlers.kosis_handler',
            DatabaseType.EXTERNAL_API: 'backend.database.handlers.api_handler'
        }
        self._handler_classes: Dict[DatabaseType, str] = {
            DatabaseType.MYSQL: 'MySQLHandler',
            DatabaseType.POSTGRESQL: 'PostgreSQLHandler',
            DatabaseType.MONGODB: 'MongoDBHandler', 
            DatabaseType.SQLITE: 'SQLiteHandler',
            DatabaseType.REDIS: 'RedisHandler',
            DatabaseType.ORACLE: 'OracleHandler',
            DatabaseType.MSSQL: 'MSSQLHandler',
            # API 핸들러들
            DatabaseType.KOSIS_API: 'KOSISHandler',
            DatabaseType.EXTERNAL_API: 'BaseAPIHandler'
        }
    
    def register_handler(self, db_type: DatabaseType, handler_class: Type[BaseDatabaseHandler]):
        """핸들러 등록"""
        self._handlers[db_type] = handler_class
        logger.info(f"Registered handler for {db_type.value}: {handler_class.__name__}")
    
    def get_handler_class(self, db_type: DatabaseType) -> Type[BaseDatabaseHandler]:
        """핸들러 클래스 조회 (지연 로딩)"""
        if db_type in self._handlers:
            return self._handlers[db_type]
        
        # 지연 로딩
        if db_type in self._handler_modules:
            try:
                module_name = self._handler_modules[db_type]
                class_name = self._handler_classes[db_type]
                
                module = importlib.import_module(module_name)
                handler_class = getattr(module, class_name)
                
                self._handlers[db_type] = handler_class
                logger.info(f"Lazy loaded handler for {db_type.value}: {class_name}")
                
                return handler_class
                
            except ImportError as e:
                logger.warning(f"Failed to import handler for {db_type.value}: {e}")
                raise DatabaseHandlerError(f"Handler for {db_type.value} not available: {e}")
            except AttributeError as e:
                logger.error(f"Handler class {class_name} not found in {module_name}: {e}")
                raise DatabaseHandlerError(f"Handler class for {db_type.value} not found: {e}")
        
        raise DatabaseHandlerError(f"No handler registered for {db_type.value}")
    
    def is_handler_available(self, db_type: DatabaseType) -> bool:
        """핸들러 사용 가능 여부 확인"""
        try:
            self.get_handler_class(db_type)
            return True
        except DatabaseHandlerError:
            return False
    
    def get_available_handlers(self) -> List[DatabaseType]:
        """사용 가능한 핸들러 목록"""
        available = []
        for db_type in DatabaseType:
            if self.is_handler_available(db_type):
                available.append(db_type)
        return available
    
    def get_handler_info(self, db_type: DatabaseType) -> Optional[Dict]:
        """핸들러 정보 조회"""
        try:
            # 핸들러 클래스만 로드해서 사용 가능 여부 확인
            handler_class = self.get_handler_class(db_type)
            
            return {
                "type": db_type.value,
                "class_name": handler_class.__name__,
                "available": True,
                "error": None
            }
        except Exception as e:
            return {
                "type": db_type.value,
                "available": False,
                "error": str(e)
            }


# 글로벌 레지스트리 인스턴스
_registry = HandlerRegistry()


class DatabaseHandlerFactory:
    """데이터베이스 핸들러 팩토리"""
    
    @staticmethod
    def create_handler(config: ConnectionConfig) -> BaseDatabaseHandler:
        """설정에 따른 핸들러 생성"""
        try:
            handler_class = _registry.get_handler_class(config.type)
            handler = handler_class(config)
            
            logger.info(f"Created {config.type.value} handler: {config.name}")
            return handler
            
        except Exception as e:
            logger.error(f"Failed to create handler for {config.type.value}: {e}")
            raise DatabaseHandlerError(f"Failed to create {config.type.value} handler: {e}")
    
    @staticmethod
    def get_supported_databases() -> List[Dict]:
        """지원하는 데이터베이스 목록"""
        databases = []
        for db_type in DatabaseType:
            info = _registry.get_handler_info(db_type)
            if info:
                databases.append(info)
        return databases
    
    @staticmethod
    def is_database_supported(db_type: DatabaseType) -> bool:
        """데이터베이스 지원 여부"""
        return _registry.is_handler_available(db_type)
    
    @staticmethod
    def validate_config(config: ConnectionConfig) -> tuple[bool, Optional[str]]:
        """연결 설정 유효성 검사"""
        try:
            # 기본 필드 검사
            if not config.name:
                return False, "Connection name is required"
            
            if not config.type:
                return False, "Database type is required"
            
            # 핸들러 사용 가능 여부 검사
            if not _registry.is_handler_available(config.type):
                return False, f"Handler for {config.type.value} is not available"
            
            # 데이터베이스별 필수 필드 검사
            if config.type in [DatabaseType.MYSQL, DatabaseType.POSTGRESQL, DatabaseType.ORACLE, DatabaseType.MSSQL]:
                if not config.host:
                    return False, "Host is required"
                if not config.username:
                    return False, "Username is required"
                if not config.database:
                    return False, "Database name is required"
            
            elif config.type == DatabaseType.MONGODB:
                if not config.connection_string and not config.host:
                    return False, "Connection string or host is required"
            
            elif config.type == DatabaseType.SQLITE:
                if not config.database:
                    return False, "Database file path is required"
            
            elif config.type == DatabaseType.REDIS:
                if not config.host:
                    return False, "Host is required"
            
            elif config.type == DatabaseType.KOSIS_API:
                if not config.password:  # API 키를 password 필드에 저장
                    return False, "KOSIS API key is required"
            
            elif config.type == DatabaseType.EXTERNAL_API:
                if not config.host:
                    return False, "API base URL is required"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {e}"


# 편의 함수들
def create_handler(config: ConnectionConfig) -> BaseDatabaseHandler:
    """핸들러 생성 편의 함수"""
    return DatabaseHandlerFactory.create_handler(config)


def get_supported_databases() -> List[Dict]:
    """지원 데이터베이스 목록 조회 편의 함수"""
    return DatabaseHandlerFactory.get_supported_databases()


def is_database_supported(db_type: DatabaseType) -> bool:
    """데이터베이스 지원 여부 편의 함수"""
    return DatabaseHandlerFactory.is_database_supported(db_type)


def validate_config(config: ConnectionConfig) -> tuple[bool, Optional[str]]:
    """설정 검증 편의 함수"""
    return DatabaseHandlerFactory.validate_config(config)


# 핸들러 레지스트리 접근 함수
def get_handler_registry() -> HandlerRegistry:
    """핸들러 레지스트리 반환"""
    return _registry 