"""
PostgreSQL Database Handler - MindsDB inspired
PostgreSQL 데이터베이스 전용 핸들러
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple

try:
    import asyncpg
    import psycopg2
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

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


class PostgreSQLHandler(BaseDatabaseHandler):
    """PostgreSQL 데이터베이스 핸들러"""
    
    def __init__(self, config: ConnectionConfig):
        if not POSTGRESQL_AVAILABLE:
            raise ImportError("PostgreSQL dependencies not available. Install with: pip install asyncpg psycopg2-binary")
        
        super().__init__(config)
        self._pool = None
    
    @property
    def type(self) -> DatabaseType:
        return DatabaseType.POSTGRESQL
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "CREATE", "DROP", "ALTER", "INDEX",
            "TRANSACTION", "PROCEDURE", "FUNCTION",
            "CTE", "WINDOW", "JSON", "ARRAY"
        ]
    
    def is_connected(self) -> bool:
        """PostgreSQL 연결 상태 확인 (오버라이드)"""
        return (self.status == ConnectionStatus.CONNECTED and 
                self._pool is not None and 
                not self._pool._closed)
    
    async def connect(self) -> bool:
        """PostgreSQL 연결"""
        try:
            self._set_status(ConnectionStatus.CONNECTING)
            
            # 연결 문자열 구성
            dsn = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host or 'localhost'}:{self.config.port or 5432}/{self.config.database}"
            
            # SSL 설정
            ssl_context = None
            if self.config.ssl:
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # PostgreSQL 연결 옵션 필터링 (schema 제외)
            connection_options = {
                k: v for k, v in self.config.options.items() 
                if k not in ['schema']  # schema는 논리적 개념이므로 연결 파라미터에서 제외
            }
            
            # 연결 풀 생성
            self._pool = await asyncpg.create_pool(
                dsn,
                ssl=ssl_context,
                min_size=1,
                max_size=10,
                command_timeout=60,
                **connection_options
            )
            
            # 연결 테스트
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                
            # connection 속성을 pool로 설정하여 is_connected()가 올바르게 작동하도록 함
            self.connection = self._pool
            self._set_status(ConnectionStatus.CONNECTED)
            self.logger.info(f"Connected to PostgreSQL: {self.config.host}:{self.config.port}/{self.config.database}")
            return True
            
        except Exception as e:
            error_msg = self.format_error(e)
            self._set_status(ConnectionStatus.ERROR, error_msg)
            self.logger.error(f"PostgreSQL connection failed: {error_msg}")
            return False
    
    async def disconnect(self) -> bool:
        """PostgreSQL 연결 해제"""
        try:
            if self._pool:
                await self._pool.close()
                self._pool = None
            
            # connection 속성도 초기화
            self.connection = None
            self._set_status(ConnectionStatus.DISCONNECTED)
            self.logger.info("Disconnected from PostgreSQL")
            return True
            
        except Exception as e:
            self.logger.error(f"PostgreSQL disconnect error: {e}")
            return False
    
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """PostgreSQL 연결 테스트"""
        try:
            start_time = time.time()
            
            # 연결 문자열 구성
            dsn = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host or 'localhost'}:{self.config.port or 5432}/{self.config.database}"
            
            # SSL 설정
            ssl_context = None
            if self.config.ssl:
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # PostgreSQL 연결 옵션 필터링 (schema 제외)
            connection_options = {
                k: v for k, v in self.config.options.items() 
                if k not in ['schema']  # schema는 논리적 개념이므로 연결 파라미터에서 제외
            }
            
            # 임시 연결로 테스트
            conn = await asyncpg.connect(dsn, ssl=ssl_context, **connection_options)
            
            version = await conn.fetchval("SELECT version()")
            connection_id = await conn.fetchval("SELECT pg_backend_pid()")
            
            await conn.close()
            
            latency = round((time.time() - start_time) * 1000, 2)
            message = f"Connected successfully (PID: {connection_id}, Latency: {latency}ms)"
            
            return True, message
            
        except Exception as e:
            return False, self.format_error(e)
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> QueryResult:
        """PostgreSQL 쿼리 실행"""
        if not self.is_connected():
            raise ConnectionError("Not connected to PostgreSQL")
        
        start_time = time.time()
        
        try:
            async with self._pool.acquire() as conn:
                # 파라미터 변환 (딕셔너리를 리스트로)
                if params:
                    param_values = list(params.values())
                    # 플레이스홀더를 $1, $2, ... 형식으로 변경
                    for i, key in enumerate(params.keys(), 1):
                        query = query.replace(f"%({key})s", f"${i}")
                        query = query.replace(f":{key}", f"${i}")
                else:
                    param_values = None
                
                # 쿼리 실행
                if query.strip().upper().startswith('SELECT') or query.strip().upper().startswith('WITH'):
                    # SELECT 쿼리
                    if param_values:
                        result = await conn.fetch(query, *param_values)
                    else:
                        result = await conn.fetch(query)
                    
                    if result:
                        columns = list(result[0].keys())
                        data = [dict(row) for row in result]
                        row_count = len(data)
                    else:
                        columns = []
                        data = []
                        row_count = 0
                else:
                    # INSERT/UPDATE/DELETE 쿼리
                    if param_values:
                        status = await conn.execute(query, *param_values)
                    else:
                        status = await conn.execute(query)
                    
                    columns = []
                    data = []
                    # 상태에서 affected rows 추출
                    row_count = int(status.split()[-1]) if status.split()[-1].isdigit() else 0
            
            execution_time = time.time() - start_time
            self._log_query(query, execution_time, True)
            
            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=row_count,
                execution_time=execution_time,
                metadata={"status": status if 'status' in locals() else None}
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
    
    async def get_tables(
        self,
        schema: Optional[str] = None,
        include_columns: bool = True,
    ) -> List[TableInfo]:
        """PostgreSQL 테이블 목록 조회"""
        try:
            schema_name = schema or 'public'

            # 미리 row count 메타데이터 조회
            row_count_map = await self._get_row_count_metadata(schema_name)

            query = """
            SELECT
                t.table_name as name,
                t.table_schema as schema_name,
                t.table_type as type,
                pg_total_relation_size(c.oid) as size_bytes,
                obj_description(c.oid) as comment
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
            WHERE t.table_schema = $1
            ORDER BY t.table_name
            """
            
            result = await self.execute_query(query, {"schema_name": schema_name})
            if not result.success:
                raise SchemaError(f"Failed to get tables: {result.error}")

            tables = []
            for row in result.data:
                # 메타데이터 기반 행 수. 없으면 테이블 제외
                row_count = None
                if row['type'] == 'BASE TABLE':
                    row_count = row_count_map.get(row['name'])
                    if row_count is None:
                        # 메타데이터가 없는 테이블은 건너뜀
                        continue

                table_info = TableInfo(
                    name=row['name'],
                    schema=row['schema_name'],
                    type=row['type'].lower().replace(' ', '_'),
                    row_count=row_count,
                    size=f"{round(row['size_bytes'] / 1024 / 1024, 2)}MB" if row['size_bytes'] else None,
                    comment=row['comment']
                )
                
                # 컬럼 정보 추가
                if include_columns:
                    table_info.columns = await self._get_table_columns(row['name'], schema_name)
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            raise SchemaError(f"Failed to get PostgreSQL tables: {e}")
    
    async def get_all_schemas(self) -> List[str]:
        """PostgreSQL 모든 스키마 목록 조회"""
        try:
            query = """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name
            """
            result = await self.execute_query(query)
            if result.success:
                return [row['schema_name'] for row in result.data]
            return []
        except Exception as e:
            logger.warning(f"Failed to get schemas: {e}")
            return []

    async def get_schema(self, include_columns: bool = True) -> SchemaInfo:
        """PostgreSQL 스키마 정보 조회 - 모든 스키마 또는 지정 스키마"""
        try:
            # 모든 스키마 조회
            all_schemas = await self.get_all_schemas()
            default_schema = self.config.options.get('schema', 'public')
            
            all_tables = []
            all_views = []
            all_procedures = []
            
            # 각 스키마별로 테이블, 뷰, 프로시저 조회
            for schema_name in all_schemas:
                try:
                    # 테이블 조회
                    tables = await self.get_tables(schema_name, include_columns)
                    all_tables.extend([t for t in tables if t.type == 'base_table'])
                    
                    # 뷰 조회
                    views_query = """
                    SELECT table_name as name, table_schema as schema_name
                    FROM information_schema.views 
                    WHERE table_schema = $1
                    """
                    result = await self.execute_query(views_query, {"schema": schema_name})
                    if result.success:
                        for row in result.data:
                            view_info = TableInfo(
                                name=row['name'],
                                schema=row['schema_name'],
                                type='view'
                            )
                            all_views.append(view_info)
                    
                    # 프로시저/함수 조회
                    procedures_query = """
                    SELECT routine_name as name, routine_type as type, routine_schema as schema_name
                    FROM information_schema.routines 
                    WHERE routine_schema = $1
                    """
                    result = await self.execute_query(procedures_query, {"schema": schema_name})
                    if result.success:
                        procedures = [
                            {"name": row['name'], "type": row['type'], "schema": row['schema_name']} 
                            for row in result.data
                        ]
                        all_procedures.extend(procedures)
                        
                except Exception as e:
                    logger.warning(f"Failed to get objects from schema {schema_name}: {e}")
                    continue
            
            return SchemaInfo(
                name=f"전체 ({len(all_schemas)} 스키마)",
                tables=all_tables,
                views=all_views,
                procedures=all_procedures
            )
            
        except Exception as e:
            raise SchemaError(f"Failed to get PostgreSQL schema: {e}")
    
    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> TableInfo:
        """PostgreSQL 특정 테이블 정보 조회"""
        try:
            schema_name = schema or 'public'
            
            # 기본 테이블 정보
            query = """
            SELECT 
                t.table_name as name,
                t.table_schema as schema_name,
                t.table_type as type,
                pg_total_relation_size(c.oid) as size_bytes,
                obj_description(c.oid) as comment
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
            WHERE t.table_schema = $1 AND t.table_name = $2
            """
            
            result = await self.execute_query(query, {"schema": schema_name, "table": table_name})
            if not result.success or not result.data:
                raise SchemaError(f"Table {table_name} not found")
            
            row = result.data[0]
            
            # 메타데이터 기반 행 수 조회
            row_count = None
            if row['type'] == 'BASE TABLE':
                row_counts = await self._get_row_count_metadata(schema_name)
                row_count = row_counts.get(table_name)

            table_info = TableInfo(
                name=row['name'],
                schema=row['schema_name'],
                type=row['type'].lower().replace(' ', '_'),
                row_count=row_count,
                size=f"{round(row['size_bytes'] / 1024 / 1024, 2)}MB" if row['size_bytes'] else None,
                comment=row['comment']
            )
            
            # 컬럼 정보 추가
            table_info.columns = await self._get_table_columns(table_name, schema_name)
            
            return table_info
            
        except Exception as e:
            raise SchemaError(f"Failed to get PostgreSQL table info: {e}")
    
    async def _get_table_columns(self, table_name: str, schema: str) -> List[Dict[str, Any]]:
        """테이블 컬럼 정보 조회"""
        query = """
        SELECT 
            c.column_name as name,
            c.data_type as type,
            c.is_nullable as nullable,
            c.column_default as default_value,
            c.character_maximum_length as max_length,
            c.numeric_precision as precision,
            c.numeric_scale as scale,
            tc.constraint_type as constraint_type
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu 
            ON c.table_name = kcu.table_name 
            AND c.column_name = kcu.column_name 
            AND c.table_schema = kcu.table_schema
        LEFT JOIN information_schema.table_constraints tc 
            ON kcu.constraint_name = tc.constraint_name 
            AND kcu.table_schema = tc.table_schema
        WHERE c.table_schema = $1 AND c.table_name = $2
        ORDER BY c.ordinal_position
        """
        
        result = await self.execute_query(query, {"schema": schema, "table": table_name})
        if not result.success:
            return []
        
        columns = []
        for row in result.data:
            column = {
                "name": row['name'],
                "type": row['type'],
                "nullable": row['nullable'] == 'YES',
                "default_value": row['default_value'],
                "primary_key": row['constraint_type'] == 'PRIMARY KEY',
                "auto_increment": 'nextval' in (row['default_value'] or '').lower(),
                "unique": row['constraint_type'] in ('PRIMARY KEY', 'UNIQUE'),
                "max_length": row['max_length'],
                "precision": row['precision'],
                "scale": row['scale']
            }
            columns.append(column)
        
        return columns

    async def _get_row_count_metadata(self, schema: str) -> Dict[str, int]:
        """pg_stat 메타데이터에서 테이블별 행 수 조회"""
        query = """
        SELECT relname as table_name, n_live_tup
        FROM pg_stat_all_tables
        WHERE schemaname = $1
        """

        result = await self.execute_query(query, {"schema": schema})
        if not result.success:
            return {}
        return {row['table_name']: row['n_live_tup'] for row in result.data if row['n_live_tup'] is not None}
    
    async def get_version(self) -> Optional[str]:
        """PostgreSQL 버전 조회"""
        try:
            result = await self.execute_query("SELECT version()")
            if result.success and result.data:
                version_info = result.data[0]['version']
                # PostgreSQL 버전만 추출
                if 'PostgreSQL' in version_info:
                    return version_info.split(',')[0]
                return version_info
        except Exception:
            pass
        return None
    
    async def get_database_size(self) -> Optional[str]:
        """PostgreSQL 데이터베이스 크기 조회"""
        try:
            query = "SELECT pg_size_pretty(pg_database_size($1)) as size"
            result = await self.execute_query(query, {"db": self.config.database})
            if result.success and result.data:
                return result.data[0]['size']
        except Exception:
            pass
        return None 