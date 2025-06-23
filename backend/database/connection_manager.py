"""
Database Connection Manager - MindsDB inspired
다중 데이터베이스 연결 관리자
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .handlers.base_handler import (
    BaseDatabaseHandler,
    DatabaseType, 
    ConnectionConfig,
    ConnectionStatus,
    QueryResult,
    TableInfo,
    SchemaInfo,
    ConnectionError,
    DatabaseHandlerError
)
from .handlers.handler_factory import create_handler, validate_config
from .connection_storage import get_connection_storage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """다중 데이터베이스 연결 관리자"""
    
    def __init__(self):
        self._connections: Dict[str, BaseDatabaseHandler] = {}
        self._active_connection_id: Optional[str] = None
        self._connection_history: List[Dict] = []
        self._lock = None  # 지연 생성
        self._storage = get_connection_storage()
        self._initialized = False
    
    async def _ensure_initialized(self):
        """지연 초기화 확인"""
        if not self._initialized:
            self._lock = asyncio.Lock()
            await self._load_saved_connections()
            self._initialized = True
    
    def _ensure_initialized_sync(self):
        """동기 메서드용 초기화 확인"""
        if not self._initialized:
            # 동기 메서드에서는 저장된 연결을 불러오지 않음
            # 첫 번째 비동기 호출에서 로드됨
            if self._lock is None:
                self._lock = None  # 비동기에서 생성
    
    async def create_connection(self, config: ConnectionConfig) -> tuple[bool, str]:
        """새 연결 생성"""
        await self._ensure_initialized()
        async with self._lock:
            try:
                # 설정 검증
                is_valid, error_msg = validate_config(config)
                if not is_valid:
                    return False, error_msg
                
                # ID가 없거나 "test"면 새로 생성
                if not config.id or config.id == "test":
                    config.id = str(uuid.uuid4())
                
                # 이미 존재하는 연결인지 확인
                if config.id in self._connections:
                    return False, f"Connection with ID {config.id} already exists"
                
                # 핸들러 생성
                handler = create_handler(config)
                
                # 연결 시도
                connected = await handler.connect()
                if not connected:
                    return False, f"Failed to connect: {handler.last_error}"
                
                # 연결 저장
                self._connections[config.id] = handler
                
                # 첫 번째 연결이면 활성 연결로 설정
                if not self._active_connection_id:
                    self._active_connection_id = config.id
                
                # 히스토리 추가
                self._add_to_history("created", config.id, config.name)
                
                # 영구 저장
                await self._save_connections()
                
                logger.info(f"Created connection: {config.name} ({config.type.value})")
                return True, config.id
                
            except Exception as e:
                error_msg = f"Failed to create connection: {e}"
                logger.error(error_msg)
                return False, error_msg
    
    async def remove_connection(self, connection_id: str) -> bool:
        """연결 제거"""
        await self._ensure_initialized()
        async with self._lock:
            try:
                if connection_id not in self._connections:
                    return False
                
                handler = self._connections[connection_id]
                
                # 연결 해제
                await handler.disconnect()
                
                # 연결 제거
                del self._connections[connection_id]
                
                # 활성 연결이었다면 다른 연결로 변경
                if self._active_connection_id == connection_id:
                    if self._connections:
                        self._active_connection_id = next(iter(self._connections.keys()))
                    else:
                        self._active_connection_id = None
                
                # 히스토리 추가
                self._add_to_history("removed", connection_id, handler.config.name)
                
                # 영구 저장
                await self._save_connections()
                
                logger.info(f"Removed connection: {handler.config.name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to remove connection {connection_id}: {e}")
                return False
    
    async def test_connection(self, connection_id: str) -> tuple[bool, Optional[str]]:
        """연결 테스트"""
        handler = self._connections.get(connection_id)
        if not handler:
            return False, "Connection not found"
        
        try:
            return await handler.test_connection()
        except Exception as e:
            return False, f"Test failed: {e}"
    
    async def test_config(self, config: ConnectionConfig) -> tuple[bool, Optional[str]]:
        """설정으로 연결 테스트 (실제 연결 생성 없이)"""
        try:
            # 설정 검증
            is_valid, error_msg = validate_config(config)
            if not is_valid:
                return False, error_msg
            
            # 임시 핸들러로 테스트
            handler = create_handler(config)
            result = await handler.test_connection()
            
            # 임시 핸들러 정리 (필요시 disconnect)
            try:
                await handler.disconnect()
            except:
                pass
            
            return result
            
        except Exception as e:
            return False, f"Connection test failed: {e}"
    
    def get_connection(self, connection_id: str) -> Optional[BaseDatabaseHandler]:
        """연결 조회"""
        return self._connections.get(connection_id)
    
    def get_active_connection(self) -> Optional[BaseDatabaseHandler]:
        """활성 연결 조회"""
        if self._active_connection_id:
            return self._connections.get(self._active_connection_id)
        return None
    
    async def set_active_connection(self, connection_id: str) -> bool:
        """활성 연결 설정"""
        if connection_id not in self._connections:
            return False
            
        handler = self._connections[connection_id]
        
        # 연결 상태 확인 및 필요시 재연결
        if not handler.is_connected():
            logger.info(f"Connection {connection_id} is not connected, attempting to reconnect...")
            connected = await handler.connect()
            if not connected:
                logger.error(f"Failed to reconnect connection {connection_id}")
                return False
        
        self._active_connection_id = connection_id
        self._add_to_history("activated", connection_id, handler.config.name)
        logger.info(f"Activated connection: {handler.config.name}")
        return True
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """모든 연결 정보 조회"""
        self._ensure_initialized_sync()
        connections = []
        for connection_id, handler in self._connections.items():
            info = handler.get_connection_info()
            info['active'] = connection_id == self._active_connection_id
            connections.append(info)
        return connections
    
    def get_connection_by_name(self, name: str) -> Optional[BaseDatabaseHandler]:
        """이름으로 연결 조회"""
        for handler in self._connections.values():
            if handler.config.name == name:
                return handler
        return None
    
    async def execute_query(self, query: str, connection_id: Optional[str] = None, params: Optional[Dict] = None) -> QueryResult:
        """쿼리 실행"""
        await self._ensure_initialized()
        # 연결 선택
        if connection_id:
            handler = self.get_connection(connection_id)
        else:
            handler = self.get_active_connection()
        
        if not handler:
            return QueryResult(
                success=False,
                error="No connection available"
            )
        
        try:
            return await handler.execute_query(query, params)
        except Exception as e:
            return QueryResult(
                success=False,
                error=f"Query execution failed: {e}"
            )
    
    async def get_tables(self, connection_id: Optional[str] = None, schema: Optional[str] = None) -> List[TableInfo]:
        """테이블 목록 조회"""
        await self._ensure_initialized()
        if connection_id:
            handler = self.get_connection(connection_id)
        else:
            handler = self.get_active_connection()
        
        if not handler:
            raise ConnectionError("No connection available")
        
        return await handler.get_tables(schema)
    
    async def get_schema(self, connection_id: Optional[str] = None) -> SchemaInfo:
        """스키마 정보 조회"""
        await self._ensure_initialized()
        if connection_id:
            handler = self.get_connection(connection_id)
        else:
            handler = self.get_active_connection()
        
        if not handler:
            raise ConnectionError("No connection available")
        
        return await handler.get_schema()
    
    async def get_table_info(self, table_name: str, connection_id: Optional[str] = None, schema: Optional[str] = None) -> TableInfo:
        """특정 테이블 정보 조회"""
        if connection_id:
            handler = self.get_connection(connection_id)
        else:
            handler = self.get_active_connection()
        
        if not handler:
            raise ConnectionError("No connection available")
        
        return await handler.get_table_info(table_name, schema)
    
    async def refresh_connection(self, connection_id: str) -> bool:
        """연결 새로고침"""
        handler = self.get_connection(connection_id)
        if not handler:
            return False
        
        try:
            # 재연결
            await handler.disconnect()
            connected = await handler.connect()
            
            if connected:
                self._add_to_history("refreshed", connection_id, handler.config.name)
            
            return connected
            
        except Exception as e:
            logger.error(f"Failed to refresh connection {connection_id}: {e}")
            return False
    
    async def check_all_connections(self) -> Dict[str, bool]:
        """모든 연결 상태 확인"""
        results = {}
        
        for connection_id, handler in self._connections.items():
            try:
                is_connected, _ = await handler.test_connection()
                results[connection_id] = is_connected
            except Exception:
                results[connection_id] = False
        
        return results
    
    async def disconnect_all(self) -> bool:
        """모든 연결 해제"""
        try:
            for handler in self._connections.values():
                await handler.disconnect()
            
            self._connections.clear()
            self._active_connection_id = None
            
            self._add_to_history("disconnected_all", "", "")
            logger.info("Disconnected all connections")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect all connections: {e}")
            return False
    
    def get_connection_history(self, limit: int = 50) -> List[Dict]:
        """연결 히스토리 조회"""
        return self._connection_history[-limit:]
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """연결 통계"""
        total = len(self._connections)
        by_type = {}
        
        for handler in self._connections.values():
            db_type = handler.type.value
            by_type[db_type] = by_type.get(db_type, 0) + 1
        
        return {
            "total_connections": total,
            "active_connection": self._active_connection_id,
            "connections_by_type": by_type,
            "history_count": len(self._connection_history)
        }
    
    def _add_to_history(self, action: str, connection_id: str, connection_name: str):
        """히스토리 추가"""
        self._connection_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "connection_id": connection_id,
            "connection_name": connection_name
        })
        
        # 히스토리 크기 제한 (최대 1000개)
        if len(self._connection_history) > 1000:
            self._connection_history = self._connection_history[-1000:]
    
    async def _load_saved_connections(self):
        """저장된 연결 정보 로드"""
        try:
            saved_configs = await self._storage.load_connections()
            
            for config_id, config in saved_configs.items():
                try:
                    # 핸들러 생성 (연결은 하지 않음)
                    handler = create_handler(config)
                    self._connections[config_id] = handler
                    
                    # 첫 번째 연결을 활성 연결로 설정
                    if not self._active_connection_id:
                        self._active_connection_id = config_id
                    
                    logger.info(f"Loaded saved connection: {config.name} ({config.type.value})")
                    
                except Exception as e:
                    logger.error(f"Failed to load connection {config.name}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self._connections)} saved connections")
            
        except Exception as e:
            logger.error(f"Failed to load saved connections: {e}")
    
    async def _save_connections(self):
        """현재 연결 정보 저장"""
        try:
            configs = {}
            for conn_id, handler in self._connections.items():
                configs[conn_id] = handler.config
            
            await self._storage.save_connections(configs)
            
        except Exception as e:
            logger.error(f"Failed to save connections: {e}")


# 글로벌 연결 매니저 인스턴스
_connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """글로벌 연결 매니저 반환"""
    return _connection_manager 