"""
SQLite Database Handler - MindsDB inspired
SQLite 데이터베이스 전용 핸들러
"""

import asyncio
import time
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
import aiosqlite
import os

from .base_handler import (
    BaseDatabaseHandler, 
    DatabaseType, 
    ConnectionStatus,
    ConnectionConfig,
    QueryResult, 
    TableInfo, 
    SchemaInfo,
    ConnectionError,
    QueryError,
    SchemaError
)


class SQLiteHandler(BaseDatabaseHandler):
    """SQLite 데이터베이스 핸들러"""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._connection = None
        self._db_path = config.database
    
    @property
    def type(self) -> DatabaseType:
        return DatabaseType.SQLITE
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "CREATE", "DROP", "ALTER", "INDEX",
            "TRANSACTION", "PRAGMA"
        ]
    
    async def connect(self) -> bool:
        """SQLite 연결"""
        try:
            self._set_status(ConnectionStatus.CONNECTING)
            
            # 파일 경로 확인
            if not self._db_path:
                raise ConnectionError("Database file path is required")
            
            # 디렉토리 생성 (필요시)
            db_dir = os.path.dirname(self._db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # 연결 생성
            self._connection = await aiosqlite.connect(self._db_path)
            self._connection.row_factory = aiosqlite.Row  # 딕셔너리 형태로 결과 반환
            
            # 연결 테스트
            async with self._connection.execute("SELECT 1") as cursor:
                result = await cursor.fetchone()
            
            self._set_status(ConnectionStatus.CONNECTED)
            self.logger.info(f"Connected to SQLite: {self._db_path}")
            return True
            
        except Exception as e:
            error_msg = self.format_error(e)
            self._set_status(ConnectionStatus.ERROR, error_msg)
            self.logger.error(f"SQLite connection failed: {error_msg}")
            return False
    
    async def disconnect(self) -> bool:
        """SQLite 연결 해제"""
        try:
            if self._connection:
                await self._connection.close()
                self._connection = None
            
            self._set_status(ConnectionStatus.DISCONNECTED)
            self.logger.info("Disconnected from SQLite")
            return True
            
        except Exception as e:
            self.logger.error(f"SQLite disconnect error: {e}")
            return False
    
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """SQLite 연결 테스트"""
        try:
            start_time = time.time()
            
            # 임시 연결로 테스트
            test_conn = await aiosqlite.connect(self._db_path)
            
            async with test_conn.execute("SELECT sqlite_version()") as cursor:
                result = await cursor.fetchone()
                version = result[0] if result else "Unknown"
            
            await test_conn.close()
            
            latency = round((time.time() - start_time) * 1000, 2)
            message = f"Connected successfully (Version: {version}, Latency: {latency}ms)"
            
            return True, message
            
        except Exception as e:
            return False, self.format_error(e)
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> QueryResult:
        """SQLite 쿼리 실행"""
        if not self.is_connected():
            raise ConnectionError("Not connected to SQLite")
        
        start_time = time.time()
        
        try:
            # 파라미터 처리 (딕셔너리를 명명된 파라미터로)
            if params:
                # SQLite는 :name 형식의 명명된 파라미터 사용
                for key, value in params.items():
                    if f":{key}" not in query and f"%({key})s" in query:
                        query = query.replace(f"%({key})s", f":{key}")
            
            # 쿼리 실행
            if query.strip().upper().startswith(('SELECT', 'WITH', 'PRAGMA')):
                # SELECT 쿼리
                if params:
                    async with self._connection.execute(query, params) as cursor:
                        rows = await cursor.fetchall()
                else:
                    async with self._connection.execute(query) as cursor:
                        rows = await cursor.fetchall()
                
                if rows:
                    columns = list(rows[0].keys())
                    data = [dict(row) for row in rows]
                    row_count = len(data)
                else:
                    columns = []
                    data = []
                    row_count = 0
            else:
                # INSERT/UPDATE/DELETE 쿼리
                if params:
                    cursor = await self._connection.execute(query, params)
                else:
                    cursor = await self._connection.execute(query)
                
                await self._connection.commit()
                
                columns = []
                data = []
                row_count = cursor.rowcount
                
                await cursor.close()
            
            execution_time = time.time() - start_time
            self._log_query(query, execution_time, True)
            
            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=row_count,
                execution_time=execution_time,
                metadata={"affected_rows": row_count}
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
        """SQLite 테이블 목록 조회"""
        try:
            query = """
            SELECT 
                name,
                type,
                sql
            FROM sqlite_master 
            WHERE type IN ('table', 'view')
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
            
            result = await self.execute_query(query)
            if not result.success:
                raise SchemaError(f"Failed to get tables: {result.error}")
            
            tables = []
            for row in result.data:
                # 행 수 조회
                row_count = None
                if row['type'] == 'table':
                    try:
                        count_result = await self.execute_query(f'SELECT COUNT(*) as count FROM "{row["name"]}"')
                        if count_result.success and count_result.data:
                            row_count = count_result.data[0]['count']
                    except:
                        pass
                
                table_info = TableInfo(
                    name=row['name'],
                    schema='main',  # SQLite는 기본적으로 main 스키마
                    type=row['type'],
                    row_count=row_count,
                    comment=None  # SQLite는 테이블 코멘트 없음
                )
                
                # 컬럼 정보 추가
                table_info.columns = await self._get_table_columns(row['name'])
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            raise SchemaError(f"Failed to get SQLite tables: {e}")
    
    async def get_schema(self) -> SchemaInfo:
        """SQLite 스키마 정보 조회"""
        try:
            tables = await self.get_tables()
            
            # 테이블과 뷰 분리
            table_list = [t for t in tables if t.type == 'table']
            view_list = [t for t in tables if t.type == 'view']
            
            return SchemaInfo(
                name='main',
                tables=table_list,
                views=view_list,
                procedures=[]  # SQLite는 저장 프로시저 없음
            )
            
        except Exception as e:
            raise SchemaError(f"Failed to get SQLite schema: {e}")
    
    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> TableInfo:
        """SQLite 특정 테이블 정보 조회"""
        try:
            # 테이블 존재 확인
            query = """
            SELECT name, type, sql
            FROM sqlite_master 
            WHERE name = ? AND type IN ('table', 'view')
            """
            
            result = await self.execute_query(query, {"name": table_name})
            if not result.success or not result.data:
                raise SchemaError(f"Table {table_name} not found")
            
            row = result.data[0]
            
            # 행 수 조회
            row_count = None
            if row['type'] == 'table':
                try:
                    count_result = await self.execute_query(f'SELECT COUNT(*) as count FROM "{table_name}"')
                    if count_result.success and count_result.data:
                        row_count = count_result.data[0]['count']
                except:
                    pass
            
            table_info = TableInfo(
                name=row['name'],
                schema='main',
                type=row['type'],
                row_count=row_count,
                comment=None
            )
            
            # 컬럼 정보 추가
            table_info.columns = await self._get_table_columns(table_name)
            
            return table_info
            
        except Exception as e:
            raise SchemaError(f"Failed to get SQLite table info: {e}")
    
    async def _get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """테이블 컬럼 정보 조회"""
        try:
            query = f"PRAGMA table_info('{table_name}')"
            result = await self.execute_query(query)
            
            if not result.success:
                return []
            
            columns = []
            for row in result.data:
                column = {
                    "name": row['name'],
                    "type": row['type'],
                    "nullable": not row['notnull'],
                    "default_value": row['dflt_value'],
                    "primary_key": bool(row['pk']),
                    "auto_increment": False,  # PRAGMA로는 확인 어려움
                    "unique": bool(row['pk'])  # PK는 자동으로 unique
                }
                columns.append(column)
            
            return columns
            
        except Exception:
            return []
    
    async def get_version(self) -> Optional[str]:
        """SQLite 버전 조회"""
        try:
            result = await self.execute_query("SELECT sqlite_version()")
            if result.success and result.data:
                return f"SQLite {result.data[0]['sqlite_version()']}"
        except Exception:
            pass
        return None
    
    async def get_database_size(self) -> Optional[str]:
        """SQLite 데이터베이스 크기 조회"""
        try:
            if os.path.exists(self._db_path):
                size_bytes = os.path.getsize(self._db_path)
                if size_bytes > 1024 * 1024:
                    return f"{round(size_bytes / 1024 / 1024, 2)}MB"
                else:
                    return f"{round(size_bytes / 1024, 2)}KB"
        except Exception:
            pass
        return None 