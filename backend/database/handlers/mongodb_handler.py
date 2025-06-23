"""
MongoDB Database Handler - MindsDB inspired
MongoDB 데이터베이스 전용 핸들러
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple

try:
    import motor.motor_asyncio
    import pymongo
    from pymongo.errors import PyMongoError
    from bson import ObjectId
    import bson
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

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


class MongoDBHandler(BaseDatabaseHandler):
    """MongoDB 데이터베이스 핸들러"""
    
    def __init__(self, config: ConnectionConfig):
        if not MONGODB_AVAILABLE:
            raise ImportError("MongoDB dependencies not available. Install with: pip install motor pymongo")
        
        super().__init__(config)
        self._client = None
        self._database = None
    
    @property
    def type(self) -> DatabaseType:
        return DatabaseType.MONGODB
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "find", "insert", "update", "delete",
            "aggregate", "index", "count",
            "distinct", "sort", "limit", "skip"
        ]
    
    async def connect(self) -> bool:
        """MongoDB 연결"""
        try:
            self._set_status(ConnectionStatus.CONNECTING)
            
            # 연결 문자열 구성
            if self.config.connection_string:
                connection_uri = self.config.connection_string
            else:
                host = self.config.host or 'localhost'
                port = self.config.port or 27017
                
                if self.config.username and self.config.password:
                    connection_uri = f"mongodb://{self.config.username}:{self.config.password}@{host}:{port}"
                else:
                    connection_uri = f"mongodb://{host}:{port}"
                
                if self.config.database:
                    connection_uri += f"/{self.config.database}"
            
            # SSL 옵션 추가
            options = self.config.options.copy() if self.config.options else {}
            if self.config.ssl:
                options['tls'] = True
                options['tlsAllowInvalidCertificates'] = True
            
            # 클라이언트 생성
            self._client = motor.motor_asyncio.AsyncIOMotorClient(
                connection_uri,
                serverSelectionTimeoutMS=5000,
                **options
            )
            
            # 연결 테스트
            await self._client.admin.command('ping')
            
            # 데이터베이스 선택
            if self.config.database:
                self._database = self._client[self.config.database]
            else:
                # 기본 데이터베이스 목록에서 첫 번째 선택
                db_names = await self._client.list_database_names()
                admin_dbs = ['admin', 'local', 'config']
                user_dbs = [db for db in db_names if db not in admin_dbs]
                if user_dbs:
                    self._database = self._client[user_dbs[0]]
                    self.config.database = user_dbs[0]
                else:
                    self._database = self._client['test']  # 기본값
                    self.config.database = 'test'
            
            self._set_status(ConnectionStatus.CONNECTED)
            self.logger.info(f"Connected to MongoDB: {self.config.host}:{self.config.port}/{self.config.database}")
            return True
            
        except Exception as e:
            error_msg = self.format_error(e)
            self._set_status(ConnectionStatus.ERROR, error_msg)
            self.logger.error(f"MongoDB connection failed: {error_msg}")
            return False
    
    async def disconnect(self) -> bool:
        """MongoDB 연결 해제"""
        try:
            if self._client:
                self._client.close()
                self._client = None
                self._database = None
            
            self._set_status(ConnectionStatus.DISCONNECTED)
            self.logger.info("Disconnected from MongoDB")
            return True
            
        except Exception as e:
            self.logger.error(f"MongoDB disconnect error: {e}")
            return False
    
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """MongoDB 연결 테스트"""
        try:
            start_time = time.time()
            
            # 연결 문자열 구성
            if self.config.connection_string:
                connection_uri = self.config.connection_string
            else:
                host = self.config.host or 'localhost'
                port = self.config.port or 27017
                
                if self.config.username and self.config.password:
                    connection_uri = f"mongodb://{self.config.username}:{self.config.password}@{host}:{port}"
                else:
                    connection_uri = f"mongodb://{host}:{port}"
            
            # 임시 클라이언트로 테스트
            options = self.config.options.copy() if self.config.options else {}
            if self.config.ssl:
                options['tls'] = True
                options['tlsAllowInvalidCertificates'] = True
            
            test_client = motor.motor_asyncio.AsyncIOMotorClient(
                connection_uri,
                serverSelectionTimeoutMS=5000,
                **options
            )
            
            # 연결 테스트
            server_info = await test_client.server_info()
            version = server_info.get('version', 'Unknown')
            
            test_client.close()
            
            latency = round((time.time() - start_time) * 1000, 2)
            message = f"Connected successfully (Version: {version}, Latency: {latency}ms)"
            
            return True, message
            
        except Exception as e:
            return False, self.format_error(e)
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> QueryResult:
        """MongoDB 쿼리 실행 (JSON 형태의 명령어)"""
        if not self.is_connected():
            raise ConnectionError("Not connected to MongoDB")
        
        start_time = time.time()
        
        try:
            # JSON 쿼리 파싱
            if isinstance(query, str):
                # MongoDB 쿼리는 JSON 형태로 받음
                query_obj = json.loads(query)
            else:
                query_obj = query
            
            operation = query_obj.get('operation', 'find')
            collection_name = query_obj.get('collection')
            
            if not collection_name:
                raise QueryError("Collection name is required")
            
            collection = self._database[collection_name]
            
            # 파라미터 적용
            if params:
                for key, value in params.items():
                    if key in query_obj:
                        query_obj[key] = value
            
            # 작업별 처리
            if operation == 'find':
                filter_query = query_obj.get('filter', {})
                projection = query_obj.get('projection')
                sort = query_obj.get('sort')
                limit = query_obj.get('limit')
                skip = query_obj.get('skip')
                
                cursor = collection.find(filter_query, projection)
                
                if sort:
                    cursor = cursor.sort(sort)
                if skip:
                    cursor = cursor.skip(skip)
                if limit:
                    cursor = cursor.limit(limit)
                
                documents = await cursor.to_list(length=None)
                data = [self._serialize_document(doc) for doc in documents]
                
                columns = list(data[0].keys()) if data else []
                row_count = len(data)
                
            elif operation == 'insert_one':
                document = query_obj.get('document', {})
                result = await collection.insert_one(document)
                data = [{"inserted_id": str(result.inserted_id)}]
                columns = ["inserted_id"]
                row_count = 1
                
            elif operation == 'insert_many':
                documents = query_obj.get('documents', [])
                result = await collection.insert_many(documents)
                data = [{"inserted_ids": [str(id) for id in result.inserted_ids]}]
                columns = ["inserted_ids"]
                row_count = len(result.inserted_ids)
                
            elif operation == 'update_one':
                filter_query = query_obj.get('filter', {})
                update = query_obj.get('update', {})
                result = await collection.update_one(filter_query, update)
                data = [{"matched_count": result.matched_count, "modified_count": result.modified_count}]
                columns = ["matched_count", "modified_count"]
                row_count = result.modified_count
                
            elif operation == 'update_many':
                filter_query = query_obj.get('filter', {})
                update = query_obj.get('update', {})
                result = await collection.update_many(filter_query, update)
                data = [{"matched_count": result.matched_count, "modified_count": result.modified_count}]
                columns = ["matched_count", "modified_count"]
                row_count = result.modified_count
                
            elif operation == 'delete_one':
                filter_query = query_obj.get('filter', {})
                result = await collection.delete_one(filter_query)
                data = [{"deleted_count": result.deleted_count}]
                columns = ["deleted_count"]
                row_count = result.deleted_count
                
            elif operation == 'delete_many':
                filter_query = query_obj.get('filter', {})
                result = await collection.delete_many(filter_query)
                data = [{"deleted_count": result.deleted_count}]
                columns = ["deleted_count"]
                row_count = result.deleted_count
                
            elif operation == 'count_documents':
                filter_query = query_obj.get('filter', {})
                count = await collection.count_documents(filter_query)
                data = [{"count": count}]
                columns = ["count"]
                row_count = 1
                
            elif operation == 'aggregate':
                pipeline = query_obj.get('pipeline', [])
                cursor = collection.aggregate(pipeline)
                documents = await cursor.to_list(length=None)
                data = [self._serialize_document(doc) for doc in documents]
                columns = list(data[0].keys()) if data else []
                row_count = len(data)
                
            else:
                raise QueryError(f"Unsupported operation: {operation}")
            
            execution_time = time.time() - start_time
            self._log_query(str(query_obj), execution_time, True)
            
            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=row_count,
                execution_time=execution_time,
                metadata={"operation": operation, "collection": collection_name}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = self.format_error(e)
            self._log_query(str(query), execution_time, False)
            
            return QueryResult(
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
    
    async def get_tables(self, schema: Optional[str] = None) -> List[TableInfo]:
        """MongoDB 컬렉션 목록 조회"""
        try:
            collections = await self._database.list_collection_names()
            
            tables = []
            for collection_name in collections:
                collection = self._database[collection_name]
                
                # 컬렉션 통계 조회
                try:
                    stats = await self._database.command("collStats", collection_name)
                    doc_count = stats.get('count', 0)
                    size_bytes = stats.get('size', 0)
                    size = f"{round(size_bytes / 1024 / 1024, 2)}MB" if size_bytes > 0 else "0MB"
                except:
                    doc_count = await collection.count_documents({})
                    size = None
                
                # 컬럼 정보 (스키마 추론)
                columns = await self._infer_schema(collection)
                
                table_info = TableInfo(
                    name=collection_name,
                    schema=self.config.database,
                    type='collection',
                    row_count=doc_count,
                    size=size,
                    columns=columns
                )
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            raise SchemaError(f"Failed to get MongoDB collections: {e}")
    
    async def get_schema(self) -> SchemaInfo:
        """MongoDB 스키마 정보 조회"""
        try:
            tables = await self.get_tables()
            
            return SchemaInfo(
                name=self.config.database,
                tables=tables,
                views=[],  # MongoDB에서는 뷰 개념이 다름
                procedures=[]  # MongoDB에서는 저장 프로시저 없음
            )
            
        except Exception as e:
            raise SchemaError(f"Failed to get MongoDB schema: {e}")
    
    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> TableInfo:
        """MongoDB 특정 컬렉션 정보 조회"""
        try:
            collection = self._database[table_name]
            
            # 컬렉션 통계
            try:
                stats = await self._database.command("collStats", table_name)
                doc_count = stats.get('count', 0)
                size_bytes = stats.get('size', 0)
                size = f"{round(size_bytes / 1024 / 1024, 2)}MB" if size_bytes > 0 else "0MB"
            except:
                doc_count = await collection.count_documents({})
                size = None
            
            # 스키마 추론
            columns = await self._infer_schema(collection)
            
            table_info = TableInfo(
                name=table_name,
                schema=self.config.database,
                type='collection',
                row_count=doc_count,
                size=size,
                columns=columns
            )
            
            return table_info
            
        except Exception as e:
            raise SchemaError(f"Failed to get MongoDB collection info: {e}")
    
    async def _infer_schema(self, collection, sample_size: int = 100) -> List[Dict[str, Any]]:
        """MongoDB 컬렉션 스키마 추론"""
        try:
            # 샘플 문서들로 스키마 추론
            pipeline = [{"$sample": {"size": sample_size}}]
            sample_docs = await collection.aggregate(pipeline).to_list(length=None)
            
            if not sample_docs:
                return []
            
            # 모든 필드 수집
            all_fields = set()
            field_types = {}
            
            for doc in sample_docs:
                for field, value in doc.items():
                    all_fields.add(field)
                    
                    # 타입 추론
                    field_type = self._get_bson_type(value)
                    if field in field_types:
                        if field_types[field] != field_type:
                            field_types[field] = 'mixed'
                    else:
                        field_types[field] = field_type
            
            # 컬럼 정보 생성
            columns = []
            for field in sorted(all_fields):
                column = {
                    "name": field,
                    "type": field_types.get(field, 'unknown'),
                    "nullable": True,  # MongoDB는 기본적으로 모든 필드가 선택적
                    "primary_key": field == '_id',
                    "unique": field == '_id',
                    "auto_increment": field == '_id'
                }
                columns.append(column)
            
            return columns
            
        except Exception:
            return []
    
    def _get_bson_type(self, value) -> str:
        """BSON 값의 타입 반환"""
        if isinstance(value, ObjectId):
            return 'ObjectId'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'double'
        elif isinstance(value, bool):
            return 'bool'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        elif value is None:
            return 'null'
        else:
            return 'unknown'
    
    def _serialize_document(self, doc: Dict) -> Dict:
        """MongoDB 문서를 JSON 직렬화 가능한 형태로 변환"""
        if not isinstance(doc, dict):
            return doc
        
        serialized = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, dict):
                serialized[key] = self._serialize_document(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_document(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value
        
        return serialized
    
    async def get_version(self) -> Optional[str]:
        """MongoDB 버전 조회"""
        try:
            server_info = await self._client.server_info()
            return server_info.get('version')
        except Exception:
            pass
        return None
    
    async def get_database_size(self) -> Optional[str]:
        """MongoDB 데이터베이스 크기 조회"""
        try:
            stats = await self._database.command("dbStats")
            size_bytes = stats.get('dataSize', 0)
            if size_bytes > 0:
                if size_bytes > 1024 * 1024 * 1024:
                    return f"{round(size_bytes / 1024 / 1024 / 1024, 2)}GB"
                else:
                    return f"{round(size_bytes / 1024 / 1024, 2)}MB"
        except Exception:
            pass
        return None 