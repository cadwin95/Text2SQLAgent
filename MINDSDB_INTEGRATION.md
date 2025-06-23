# MindsDB-Inspired Multi-Database Integration System

**Text2SQL Agent**에 MindsDB 아키텍처를 참고한 확장성 있는 다중 데이터베이스 지원 시스템을 구현했습니다.

## 🏗️ **아키텍처 개요**

### MindsDB 참고 구조
```
backend/database/
├── handlers/
│   ├── base_handler.py          # 베이스 핸들러 (추상 클래스)
│   ├── mysql_handler.py         # MySQL 전용 핸들러
│   ├── postgresql_handler.py    # PostgreSQL 전용 핸들러
│   ├── mongodb_handler.py       # MongoDB 전용 핸들러
│   ├── sqlite_handler.py        # SQLite 전용 핸들러
│   └── handler_factory.py       # 핸들러 팩토리 & 레지스트리
├── connection_manager.py        # 연결 관리자
└── api/
    └── database_api.py          # REST API 엔드포인트
```

## 🎯 **핵심 특징**

### 1. **확장 가능한 핸들러 시스템**
- **베이스 핸들러**: 모든 DB 핸들러의 공통 인터페이스
- **타입별 핸들러**: 각 데이터베이스의 특성에 맞는 구현
- **지연 로딩**: 필요한 핸들러만 동적으로 로드
- **레지스트리 패턴**: 핸들러 등록 및 관리

### 2. **지원 데이터베이스**
- ✅ **MySQL** (aiomysql)
- ✅ **PostgreSQL** (asyncpg)  
- ✅ **MongoDB** (motor)
- ✅ **SQLite** (aiosqlite)
- 🔄 **Redis** (준비중)
- 🔄 **Oracle** (선택적)
- 🔄 **SQL Server** (선택적)

### 3. **통합 연결 관리**
- **다중 연결**: 여러 데이터베이스 동시 연결
- **활성 연결**: 기본 연결 설정 및 전환
- **상태 모니터링**: 실시간 연결 상태 확인
- **자동 재연결**: 연결 끊김 시 자동 복구

## 📋 **API 엔드포인트**

### 연결 관리
```http
# 지원 DB 타입 조회
GET /api/database/supported

# 연결 테스트
POST /api/database/connections/test

# 연결 생성
POST /api/database/connections

# 연결 목록
GET /api/database/connections

# 연결 활성화
PUT /api/database/connections/{id}/activate

# 연결 삭제
DELETE /api/database/connections/{id}
```

### 쿼리 실행
```http
# 쿼리 실행
POST /api/database/query

# 스키마 조회
GET /api/database/schema

# 테이블 목록
GET /api/database/schema/tables

# 테이블 정보
GET /api/database/schema/tables/{name}
```

### 상태 모니터링
```http
# 시스템 상태
GET /api/database/status

# 헬스 체크
GET /api/database/health

# 연결 히스토리
GET /api/database/history
```

## 🛠️ **사용 예시**

### 1. MySQL 연결
```python
# 연결 설정
connection_config = {
    "name": "MySQL Production",
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "database": "myapp",
    "username": "user",
    "password": "pass"
}

# 연결 생성
POST /api/database/connections
```

### 2. MongoDB 연결  
```python
# MongoDB 연결
connection_config = {
    "name": "MongoDB Cluster",
    "type": "mongodb", 
    "connection_string": "mongodb://user:pass@cluster.mongodb.net/mydb"
}
```

### 3. 쿼리 실행
```python
# SQL 쿼리
query_request = {
    "query": "SELECT * FROM users WHERE active = 1",
    "connection_id": "mysql-conn-id"
}

# MongoDB 쿼리 (JSON 형태)
mongo_query = {
    "query": {
        "operation": "find",
        "collection": "users", 
        "filter": {"active": True}
    },
    "connection_id": "mongo-conn-id"
}
```

## 🔧 **핸들러 구현 가이드**

### 새로운 데이터베이스 핸들러 추가
```python
# 1. 베이스 핸들러 상속
class MyDBHandler(BaseDatabaseHandler):
    @property
    def type(self) -> DatabaseType:
        return DatabaseType.MYDB
    
    @property
    def supported_operations(self) -> List[str]:
        return ["SELECT", "INSERT", "UPDATE", "DELETE"]
    
    async def connect(self) -> bool:
        # 연결 로직 구현
        pass
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> QueryResult:
        # 쿼리 실행 로직 구현
        pass

# 2. 팩토리에 등록
registry.register_handler(DatabaseType.MYDB, MyDBHandler)
```

## 📊 **데이터 모델**

### 연결 설정
```python
@dataclass
class ConnectionConfig:
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
```

### 쿼리 결과
```python
@dataclass
class QueryResult:
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
```

## 🚀 **설치 및 실행**

### 1. 의존성 설치
```bash
# 기본 패키지
pip install fastapi uvicorn

# 데이터베이스 드라이버들
pip install aiomysql asyncpg motor aiosqlite
```

### 2. 서버 실행
```bash
# 개발 모드
uvicorn backend.main:app --reload --port 8000

# 프로덕션 모드  
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 3. API 테스트
```bash
# 헬스 체크
curl http://localhost:8000/health

# 지원 DB 조회
curl http://localhost:8000/api/database/supported

# 연결 테스트
curl -X POST http://localhost:8000/api/database/connections/test \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "type": "sqlite", "database": "test.db"}'
```

## 🔐 **보안 고려사항**

### 1. 민감 정보 보호
- 연결 정보 암호화 저장
- 환경 변수로 민감 정보 관리
- API 키 기반 인증

### 2. 연결 제한
- 최대 연결 수 제한
- 타임아웃 설정
- 리소스 사용량 모니터링

## 📈 **성능 최적화**

### 1. 연결 풀링
- 데이터베이스별 연결 풀 관리
- 동적 크기 조정
- 유휴 연결 정리

### 2. 쿼리 최적화
- 쿼리 실행 시간 모니터링
- 슬로우 쿼리 로깅
- 결과 캐싱 (선택적)

## 🔄 **향후 개선사항**

### 1. 고급 기능
- [ ] 쿼리 플랜 분석
- [ ] 자동 인덱스 추천
- [ ] 데이터 타입 변환
- [ ] 크로스 DB 조인

### 2. 모니터링
- [ ] 메트릭 수집
- [ ] 대시보드 구축
- [ ] 알림 시스템
- [ ] 로그 분석

### 3. 확장성
- [ ] 분산 연결 관리
- [ ] 로드 밸런싱
- [ ] 캐시 계층
- [ ] 백업/복구

## 📖 **참고 자료**

- [MindsDB Architecture](https://github.com/mindsdb/mindsdb)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Async Database Drivers](https://docs.python.org/3/library/asyncio.html)

---

이 시스템은 MindsDB의 확장 가능한 아키텍처를 참고하여, 다양한 데이터베이스를 통합 관리할 수 있는 강력하고 유연한 플랫폼을 제공합니다. 