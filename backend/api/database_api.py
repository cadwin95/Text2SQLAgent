"""
Database API - MindsDB inspired multi-database endpoints
다중 데이터베이스 REST API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from ..database.connection_manager import get_connection_manager, ConnectionManager
from ..database.handlers.base_handler import (
    DatabaseType, 
    ConnectionConfig, 
    QueryResult,
    TableInfo,
    SchemaInfo,
    ConnectionError,
    DatabaseHandlerError
)
from ..database.handlers.handler_factory import get_supported_databases

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/database", tags=["database"])


# Pydantic 모델들
class ConnectionCreateRequest(BaseModel):
    id: Optional[str] = Field(None, description="연결 ID (미지정시 자동 생성)")
    name: str = Field(..., description="연결 이름")
    type: str = Field(..., description="데이터베이스 타입")
    host: Optional[str] = Field(None, description="호스트")
    port: Optional[int] = Field(None, description="포트")
    database: Optional[str] = Field(None, description="데이터베이스명")
    username: Optional[str] = Field(None, description="사용자명")
    password: Optional[str] = Field(None, description="비밀번호")
    ssl: bool = Field(False, description="SSL 사용")
    connection_string: Optional[str] = Field(None, description="연결 문자열")
    schema: Optional[str] = Field(None, description="기본 스키마 (PostgreSQL)")
    options: Optional[Dict[str, Any]] = Field(None, description="추가 옵션")


class ConnectionTestRequest(BaseModel):
    name: str
    type: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: bool = False
    connection_string: Optional[str] = None
    schema: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    query: str = Field(..., description="실행할 쿼리")
    connection_id: Optional[str] = Field(None, description="연결 ID (미지정시 활성 연결)")
    params: Optional[Dict[str, Any]] = Field(None, description="쿼리 파라미터")


class ConnectionResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]
    connected_at: Optional[str]
    last_error: Optional[str]
    active: bool


class QueryResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TableResponse(BaseModel):
    name: str
    table_schema: Optional[str] = Field(None, alias="schema")
    type: str
    row_count: Optional[int]
    size: Optional[str]
    comment: Optional[str]
    columns: List[Dict[str, Any]]


class SchemaResponse(BaseModel):
    name: str
    tables: List[TableResponse]
    views: List[TableResponse]
    procedures: List[Dict[str, Any]]


# 의존성
def get_db_manager() -> ConnectionManager:
    """ConnectionManager 의존성 주입 함수"""
    try:
        manager = get_connection_manager()
        logger.debug("ConnectionManager 의존성 주입 성공")
        return manager
    except Exception as e:
        logger.error(f"Failed to get connection manager: {e}")
        raise HTTPException(status_code=500, detail=f"Database manager initialization failed: {e}")


# 연결 관련 엔드포인트
@router.get("/supported", response_model=List[Dict[str, Any]])
async def get_supported_database_types():
    """지원하는 데이터베이스 타입 목록"""
    try:
        return get_supported_databases()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connections/test")
async def test_database_connection(
    request: ConnectionTestRequest,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 연결 테스트"""
    try:
        # ConnectionManager 초기화 보장
        await manager._ensure_initialized()
        
        # DatabaseType enum 변환
        try:
            db_type = DatabaseType(request.type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {request.type}")
        
        # options 처리 - 스키마 정보 추가
        options = request.options or {}
        
        # PostgreSQL의 경우 스키마 정보를 options에 저장
        if db_type == DatabaseType.POSTGRESQL and request.schema:
            options['schema'] = request.schema
        
        config = ConnectionConfig(
            id="test",
            name=request.name,
            type=db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password,
            ssl=request.ssl,
            connection_string=request.connection_string,
            options=options
        )
        
        success, message = await manager.test_config(config)
        
        return {
            "success": success,
            "message": message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {e}")


@router.post("/connections", response_model=Dict[str, Any])
async def create_database_connection(
    request: ConnectionCreateRequest,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """새 데이터베이스 연결 생성"""
    try:
        # ConnectionManager 초기화 보장
        await manager._ensure_initialized()
        
        # DatabaseType enum 변환
        try:
            db_type = DatabaseType(request.type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {request.type}")
        
        # options 처리 - 스키마 정보 추가
        options = request.options or {}
        
        # PostgreSQL의 경우 스키마 정보를 options에 저장
        if db_type == DatabaseType.POSTGRESQL and hasattr(request, 'schema') and request.schema:
            options['schema'] = request.schema
        
        config = ConnectionConfig(
            id=request.id,  # 클라이언트에서 제공한 ID 사용
            name=request.name,
            type=db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password,
            ssl=request.ssl,
            connection_string=request.connection_string,
            options=options
        )
        
        success, result = await manager.create_connection(config)
        
        if success:
            return {
                "success": True,
                "connection_id": result,
                "message": f"Connection '{request.name}' created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create connection: {e}")


@router.get("/connections", response_model=List[ConnectionResponse])
async def get_database_connections(
    manager: ConnectionManager = Depends(get_db_manager)
):
    """모든 데이터베이스 연결 목록 조회"""
    try:
        # ConnectionManager 초기화 보장
        await manager._ensure_initialized()
        connections = manager.get_all_connections()
        return [ConnectionResponse(**conn) for conn in connections]
    except Exception as e:
        logger.error(f"Failed to get connections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get connections: {e}")


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
async def get_database_connection(
    connection_id: str,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """특정 데이터베이스 연결 정보 조회"""
    try:
        handler = manager.get_connection(connection_id)
        if not handler:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        info = handler.get_connection_info()
        info['active'] = manager._active_connection_id == connection_id
        
        return ConnectionResponse(**info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection info: {e}")


@router.put("/connections/{connection_id}/activate")
async def activate_database_connection(
    connection_id: str,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 연결을 활성 연결로 설정"""
    try:
        # ConnectionManager 초기화 보장
        await manager._ensure_initialized()
        
        success = await manager.set_active_connection(connection_id)
        if success:
            return {"success": True, "message": "Connection activated"}
        else:
            raise HTTPException(status_code=404, detail="Connection not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate connection: {e}")


@router.delete("/connections/{connection_id}")
async def delete_database_connection(
    connection_id: str,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 연결 삭제"""
    try:
        success = await manager.remove_connection(connection_id)
        if success:
            return {"success": True, "message": "Connection deleted"}
        else:
            raise HTTPException(status_code=404, detail="Connection not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete connection: {e}")


@router.post("/connections/{connection_id}/test")
async def test_existing_connection(
    connection_id: str,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """기존 데이터베이스 연결 테스트"""
    try:
        success, message = await manager.test_connection(connection_id)
        return {
            "success": success,
            "message": message
        }
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {e}")


@router.post("/connections/{connection_id}/refresh")
async def refresh_database_connection(
    connection_id: str,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 연결 새로고침"""
    try:
        success = await manager.refresh_connection(connection_id)
        if success:
            return {"success": True, "message": "Connection refreshed"}
        else:
            raise HTTPException(status_code=404, detail="Connection not found")
    except Exception as e:
        logger.error(f"Failed to refresh connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh connection: {e}")


# 쿼리 관련 엔드포인트
@router.post("/query", response_model=QueryResponse)
async def execute_database_query(
    request: QueryRequest,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 쿼리 실행"""
    try:
        result = await manager.execute_query(
            request.query,
            request.connection_id,
            request.params
        )
        
        return QueryResponse(
            success=result.success,
            data=result.data,
            columns=result.columns,
            row_count=result.row_count,
            execution_time=result.execution_time,
            error=result.error,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return QueryResponse(
            success=False,
            error=f"Query execution failed: {e}"
        )


# 스키마 관련 엔드포인트
@router.get("/schema/tables", response_model=List[TableResponse])
async def get_database_tables(
    connection_id: Optional[str] = None,
    schema: Optional[str] = None,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 테이블 목록 조회"""
    try:
        tables = await manager.get_tables(connection_id, schema)
        return [
            TableResponse(
                name=table.name,
                table_schema=table.schema,
                type=table.type,
                row_count=table.row_count,
                size=table.size,
                comment=table.comment,
                columns=table.columns
            )
            for table in tables
        ]
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {e}")


@router.get("/schema", response_model=SchemaResponse)
async def get_database_schema(
    connection_id: Optional[str] = None,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 스키마 정보 조회"""
    try:
        # ConnectionManager 초기화 보장
        await manager._ensure_initialized()
        
        # 연결 확인
        if connection_id:
            connection = manager.get_connection(connection_id)
            if not connection:
                available_connections = manager.get_all_connections()
                logger.warning(f"Connection {connection_id} not found. Available: {[c['id'] for c in available_connections]}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Connection '{connection_id}' not found. Available connections: {len(available_connections)}"
                )
        else:
            # 활성 연결 확인
            active_connection = manager.get_active_connection()
            if not active_connection:
                all_connections = manager.get_all_connections()
                if not all_connections:
                    raise HTTPException(
                        status_code=400, 
                        detail="No database connections available. Please create and activate a connection first."
                    )
                else:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"No active connection. Please activate one of {len(all_connections)} available connections."
                    )
        
        schema = await manager.get_schema(connection_id)
        
        return SchemaResponse(
            name=schema.name,
            tables=[
                TableResponse(
                    name=table.name,
                    table_schema=table.schema,
                    type=table.type,
                    row_count=table.row_count,
                    size=table.size,
                    comment=table.comment,
                    columns=table.columns
                )
                for table in schema.tables
            ],
            views=[
                TableResponse(
                    name=view.name,
                    table_schema=view.schema,
                    type=view.type,
                    row_count=view.row_count,
                    size=view.size,
                    comment=view.comment,
                    columns=view.columns
                )
                for view in schema.views
            ],
            procedures=schema.procedures
        )
        
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {e}")


@router.get("/schema/tables/{table_name}", response_model=TableResponse)
async def get_table_info(
    table_name: str,
    connection_id: Optional[str] = None,
    schema: Optional[str] = None,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """특정 테이블 정보 조회"""
    try:
        table = await manager.get_table_info(table_name, connection_id, schema)
        
        return TableResponse(
            name=table.name,
            table_schema=table.schema,
            type=table.type,
            row_count=table.row_count,
            size=table.size,
            comment=table.comment,
            columns=table.columns
        )
        
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get table info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get table info: {e}")


# 상태 및 통계 엔드포인트
@router.get("/status")
async def get_database_status(
    manager: ConnectionManager = Depends(get_db_manager)
):
    """데이터베이스 연결 상태 조회"""
    try:
        stats = manager.get_connection_stats()
        return {
            "status": "ok",
            "stats": stats,
            "timestamp": manager.get_connection_history(1)[0]["timestamp"] if manager.get_connection_history(1) else None
        }
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@router.get("/health")
async def check_connections_health(
    manager: ConnectionManager = Depends(get_db_manager)
):
    """모든 연결 상태 확인"""
    try:
        health_status = await manager.check_all_connections()
        return {
            "healthy": all(health_status.values()),
            "connections": health_status,
            "total": len(health_status),
            "healthy_count": sum(health_status.values())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@router.get("/history")
async def get_connection_history(
    limit: int = 50,
    manager: ConnectionManager = Depends(get_db_manager)
):
    """연결 히스토리 조회"""
    try:
        history = manager.get_connection_history(limit)
        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {e}") 