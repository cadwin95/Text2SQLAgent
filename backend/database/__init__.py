"""
Database Package
Multi-database handlers and connection management
"""

from .connection_manager import get_connection_manager, ConnectionManager
from .handlers.base_handler import (
    BaseDatabaseHandler,
    DatabaseType,
    ConnectionConfig,
    QueryResult,
    TableInfo,
    SchemaInfo,
    ConnectionStatus
)
from .handlers.handler_factory import (
    create_handler,
    get_supported_databases,
    is_database_supported,
    validate_config
)

__all__ = [
    # Connection Management
    "get_connection_manager",
    "ConnectionManager",
    
    # Base Types
    "BaseDatabaseHandler",
    "DatabaseType", 
    "ConnectionConfig",
    "QueryResult",
    "TableInfo",
    "SchemaInfo",
    "ConnectionStatus",
    
    # Factory Functions
    "create_handler",
    "get_supported_databases", 
    "is_database_supported",
    "validate_config"
] 