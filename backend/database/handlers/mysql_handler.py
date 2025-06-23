"""
MySQL Database Handler - MindsDB inspired
MySQL 데이터베이스 전용 핸들러
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple

try:
    import aiomysql
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

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


class MySQLHandler(BaseDatabaseHandler):
    """MySQL 데이터베이스 핸들러"""
    
    def __init__(self, config: ConnectionConfig):
        if not MYSQL_AVAILABLE:
            raise ImportError("MySQL dependencies not available. Install with: pip install aiomysql pymysql")
        
        super().__init__(config)
        self._pool = None
    
    @property
    def type(self) -> DatabaseType:
        return DatabaseType.MYSQL
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "CREATE", "DROP", "ALTER", "INDEX",
            "TRANSACTION", "PROCEDURE", "FUNCTION"
        ]
    
    async def connect(self) -> bool:
        """MySQL 연결"""
        try:
            self._set_status(ConnectionStatus.CONNECTING)
            
            # 연결 풀 생성
            self._pool = await aiomysql.create_pool(
                host=self.config.host or 'localhost',
                port=self.config.port or 3306,
                user=self.config.username,
                password=self.config.password,
                db=self.config.database,
                charset='utf8mb4',
                cursorclass=aiomysql.DictCursor,
                autocommit=True,
                minsize=1,
                maxsize=10,
                **self.config.options
            )
            
            # 연결 테스트
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    
            self._set_status(ConnectionStatus.CONNECTED)
            self.logger.info(f"Connected to MySQL: {self.config.host}:{self.config.port}/{self.config.database}")
            return True
            
        except Exception as e:
            error_msg = self.format_error(e)
            self._set_status(ConnectionStatus.ERROR, error_msg)
            self.logger.error(f"MySQL connection failed: {error_msg}")
            return False
    
    async def disconnect(self) -> bool:
        """MySQL 연결 해제"""
        try:
            if self._pool:
                self._pool.close()
                await self._pool.wait_closed()
                self._pool = None
            
            self._set_status(ConnectionStatus.DISCONNECTED)
            self.logger.info("Disconnected from MySQL")
            return True
            
        except Exception as e:
            self.logger.error(f"MySQL disconnect error: {e}")
            return False
    
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """MySQL 연결 테스트"""
        try:
            start_time = time.time()
            
            # 임시 연결로 테스트
            conn = await aiomysql.connect(
                host=self.config.host or 'localhost',
                port=self.config.port or 3306,
                user=self.config.username,
                password=self.config.password,
                db=self.config.database,
                charset='utf8mb4',
                **self.config.options
            )
            
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT VERSION(), CONNECTION_ID()")
                result = await cursor.fetchone()
                version = result[0] if result else "Unknown"
            
            conn.close()
            
            latency = round((time.time() - start_time) * 1000, 2)
            message = f"Connected successfully (Version: {version}, Latency: {latency}ms)"
            
            return True, message
            
        except Exception as e:
            return False, self.format_error(e)
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> QueryResult:
        """MySQL 쿼리 실행"""
        if not self.is_connected():
            raise ConnectionError("Not connected to MySQL")
        
        start_time = time.time()
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 파라미터 처리
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    
                    # 결과 처리
                    if cursor.description:
                        # SELECT 쿼리
                        columns = [desc[0] for desc in cursor.description]
                        data = await cursor.fetchall()
                        row_count = len(data)
                    else:
                        # INSERT/UPDATE/DELETE 쿼리
                        columns = []
                        data = []
                        row_count = cursor.rowcount
            
            execution_time = time.time() - start_time
            self._log_query(query, execution_time, True)
            
            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=row_count,
                execution_time=execution_time,
                metadata={
                    "affected_rows": cursor.rowcount,
                    "last_insert_id": cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
                }
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
        """MySQL 테이블 목록 조회"""
        try:
            database = schema or self.config.database
            
            query = """
            SELECT 
                TABLE_NAME as name,
                TABLE_SCHEMA as schema_name,
                TABLE_TYPE as type,
                TABLE_ROWS as row_count,
                ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) as size_mb,
                TABLE_COMMENT as comment,
                ENGINE
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
            """
            
            result = await self.execute_query(query, (database,))
            if not result.success:
                raise SchemaError(f"Failed to get tables: {result.error}")
            
            tables = []
            for row in result.data:
                table_info = TableInfo(
                    name=row['name'],
                    schema=row['schema_name'],
                    type=row['type'].lower(),
                    row_count=row['row_count'],
                    size=f"{row['size_mb']}MB" if row['size_mb'] else None,
                    comment=row['comment']
                )
                
                # 컬럼 정보 추가
                table_info.columns = await self._get_table_columns(row['name'], database)
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            raise SchemaError(f"Failed to get MySQL tables: {e}")
    
    async def get_schema(self) -> SchemaInfo:
        """MySQL 스키마 정보 조회"""
        try:
            tables = await self.get_tables()
            
            # 뷰 조회
            views_query = """
            SELECT TABLE_NAME as name, TABLE_SCHEMA as schema_name
            FROM information_schema.VIEWS 
            WHERE TABLE_SCHEMA = %s
            """
            result = await self.execute_query(views_query, (self.config.database,))
            views = []
            if result.success:
                for row in result.data:
                    view_info = TableInfo(
                        name=row['name'],
                        schema=row['schema_name'],
                        type='view'
                    )
                    views.append(view_info)
            
            # 프로시저 조회
            procedures_query = """
            SELECT ROUTINE_NAME as name, ROUTINE_TYPE as type
            FROM information_schema.ROUTINES 
            WHERE ROUTINE_SCHEMA = %s
            """
            result = await self.execute_query(procedures_query, (self.config.database,))
            procedures = []
            if result.success:
                procedures = [
                    {"name": row['name'], "type": row['type']} 
                    for row in result.data
                ]
            
            return SchemaInfo(
                name=self.config.database,
                tables=[t for t in tables if t.type == 'table'],
                views=views,
                procedures=procedures
            )
            
        except Exception as e:
            raise SchemaError(f"Failed to get MySQL schema: {e}")
    
    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> TableInfo:
        """MySQL 특정 테이블 정보 조회"""
        try:
            database = schema or self.config.database
            
            # 기본 테이블 정보
            query = """
            SELECT 
                TABLE_NAME as name,
                TABLE_SCHEMA as schema_name,
                TABLE_TYPE as type,
                TABLE_ROWS as row_count,
                ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) as size_mb,
                TABLE_COMMENT as comment,
                ENGINE
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """
            
            result = await self.execute_query(query, (database, table_name))
            if not result.success or not result.data:
                raise SchemaError(f"Table {table_name} not found")
            
            row = result.data[0]
            table_info = TableInfo(
                name=row['name'],
                schema=row['schema_name'],
                type=row['type'].lower(),
                row_count=row['row_count'],
                size=f"{row['size_mb']}MB" if row['size_mb'] else None,
                comment=row['comment']
            )
            
            # 컬럼 정보 추가
            table_info.columns = await self._get_table_columns(table_name, database)
            
            return table_info
            
        except Exception as e:
            raise SchemaError(f"Failed to get MySQL table info: {e}")
    
    async def _get_table_columns(self, table_name: str, database: str) -> List[Dict[str, Any]]:
        """테이블 컬럼 정보 조회"""
        query = """
        SELECT 
            COLUMN_NAME as name,
            DATA_TYPE as type,
            IS_NULLABLE as nullable,
            COLUMN_DEFAULT as default_value,
            COLUMN_KEY as key_type,
            EXTRA as extra,
            COLUMN_COMMENT as comment,
            CHARACTER_MAXIMUM_LENGTH as max_length,
            NUMERIC_PRECISION as precision,
            NUMERIC_SCALE as scale
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """
        
        result = await self.execute_query(query, (database, table_name))
        if not result.success:
            return []
        
        columns = []
        for row in result.data:
            column = {
                "name": row['name'],
                "type": row['type'],
                "nullable": row['nullable'] == 'YES',
                "default_value": row['default_value'],
                "primary_key": row['key_type'] == 'PRI',
                "auto_increment": 'auto_increment' in (row['extra'] or '').lower(),
                "unique": row['key_type'] in ('PRI', 'UNI'),
                "comment": row['comment'],
                "max_length": row['max_length'],
                "precision": row['precision'],
                "scale": row['scale']
            }
            columns.append(column)
        
        return columns
    
    async def get_version(self) -> Optional[str]:
        """MySQL 버전 조회"""
        try:
            result = await self.execute_query("SELECT VERSION()")
            if result.success and result.data:
                return result.data[0]['VERSION()']
        except Exception:
            pass
        return None
    
    async def get_database_size(self) -> Optional[str]:
        """MySQL 데이터베이스 크기 조회"""
        try:
            query = """
            SELECT ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
            """
            result = await self.execute_query(query, (self.config.database,))
            if result.success and result.data:
                size_mb = result.data[0]['size_mb']
                if size_mb:
                    return f"{size_mb}MB"
        except Exception:
            pass
        return None 