"""
Database Handlers Package
Individual database type handlers
"""

from .base_handler import (
    BaseDatabaseHandler,
    DatabaseType,
    ConnectionConfig,
    QueryResult,
    TableInfo,
    SchemaInfo,
    ConnectionStatus,
    DatabaseHandlerError,
    ConnectionError,
    QueryError,
    SchemaError
)

from .handler_factory import (
    DatabaseHandlerFactory,
    HandlerRegistry,
    create_handler,
    get_supported_databases,
    is_database_supported,
    validate_config,
    get_handler_registry
)

# Lazy imports for handlers
def get_mysql_handler():
    """MySQL 핸들러 지연 로딩"""
    try:
        from .mysql_handler import MySQLHandler
        return MySQLHandler
    except ImportError:
        return None

def get_postgresql_handler():
    """PostgreSQL 핸들러 지연 로딩"""
    try:
        from .postgresql_handler import PostgreSQLHandler
        return PostgreSQLHandler
    except ImportError:
        return None

def get_mongodb_handler():
    """MongoDB 핸들러 지연 로딩"""
    try:
        from .mongodb_handler import MongoDBHandler
        return MongoDBHandler
    except ImportError:
        return None

def get_sqlite_handler():
    """SQLite 핸들러 지연 로딩"""
    try:
        from .sqlite_handler import SQLiteHandler
        return SQLiteHandler
    except ImportError:
        return None

__all__ = [
    # Base Classes
    "BaseDatabaseHandler",
    "DatabaseType",
    "ConnectionConfig", 
    "QueryResult",
    "TableInfo",
    "SchemaInfo",
    "ConnectionStatus",
    
    # Exceptions
    "DatabaseHandlerError",
    "ConnectionError", 
    "QueryError",
    "SchemaError",
    
    # Factory
    "DatabaseHandlerFactory",
    "HandlerRegistry",
    "create_handler",
    "get_supported_databases",
    "is_database_supported", 
    "validate_config",
    "get_handler_registry",
    
    # Handler Getters
    "get_mysql_handler",
    "get_postgresql_handler",
    "get_mongodb_handler", 
    "get_sqlite_handler"
] 