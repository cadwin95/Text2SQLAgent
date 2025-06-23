# 📊 Text2SQL Agent

> **MindsDB 스타일 다중 데이터베이스 통합 시스템**  
> SQL과 API를 통일된 인터페이스로 관리하는 차세대 데이터 분석 플랫폼

## 🚀 **핵심 기능**

### 🗄️ **다중 데이터베이스 지원**
- **전통적 DB**: MySQL, PostgreSQL, MongoDB, SQLite
- **API 연결**: KOSIS API, External REST APIs
- **통일된 인터페이스**로 모든 데이터소스 관리

### 🎨 **IDE 스타일 인터페이스**
- **실시간 쿼리 에디터** (SQL Syntax Highlighting)
- **시각적 스키마 탐색**
- **결과 테이블 & 차트 시각화**
- **다중 연결 관리**

### 🤖 **AI 기반 Text2SQL**
- 자연어 질문 → SQL 쿼리 자동 변환
- KOSIS 통계 데이터 자연어 검색
- 쿼리 최적화 제안

---

## 🏗️ **시스템 아키텍처**

### **MindsDB 스타일 핸들러 시스템**
```
Frontend (Next.js + TypeScript)
    ↓ REST API
Backend (FastAPI)
    ↓ Handler Factory
Database Handlers
    ├── MySQLHandler      (aiomysql)
    ├── PostgreSQLHandler (asyncpg)
    ├── MongoDBHandler    (motor)
    ├── SQLiteHandler     (aiosqlite)
    └── API Handlers
        ├── KOSISHandler     (한국 통계청 API)
        └── ExternalAPIHandler (범용 REST API)
```

### **주요 컴포넌트**
- **핸들러 팩토리**: 지연 로딩으로 효율적 핸들러 관리
- **연결 관리자**: 다중 연결 상태 실시간 모니터링
- **API 핸들러**: SQL-like 쿼리 → API 호출 자동 변환

---

## 🚀 **빠른 시작**

### **1. 환경 설정**
```bash
# 레포지토리 클론
git clone <repository-url>
cd text2sqlagent

# 환경 변수 설정
cp env.example .env
# .env 파일에서 API 키 설정
```

### **2. 백엔드 실행**
```bash
# Python 의존성 설치
pip install -r requirements.txt

# 백엔드 서버 시작
python -m backend.main
# 🚀 http://localhost:8000 에서 실행
```

### **3. 프론트엔드 실행**
```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# Node.js 의존성 설치
npm install

# 개발 서버 시작
npm run dev
# 🎨 http://localhost:3000 에서 실행
```

---

## 💡 **사용 예시**

### **KOSIS API 쿼리**
```sql
-- 통계 데이터 검색
SELECT * FROM statistics_search WHERE searchNm = '인구 현황'

-- 특정 통계표 데이터 조회
SELECT * FROM statistics_data 
WHERE orgId = '101' AND tblId = 'DT_1B01001'
AND startPrdDe = '2020' AND endPrdDe = '2023'
```

### **전통적 데이터베이스**
```sql
-- MySQL 연결 후
SELECT u.name, COUNT(o.id) as order_count
FROM users u 
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id
ORDER BY order_count DESC
```

### **자연어 질문 (AI 기능)**
```
"2023년 서울시 인구수를 보여줘"
→ KOSIS API 검색 및 데이터 조회

"최근 1년간 매출이 높은 고객 TOP 10"
→ MySQL 쿼리 자동 생성 및 실행
```

---

## 📊 **API 엔드포인트**

### **연결 관리**
```http
GET    /api/database/supported              # 지원 DB 타입 목록
POST   /api/database/connections/test       # 연결 테스트
POST   /api/database/connections            # 새 연결 생성
GET    /api/database/connections            # 연결 목록 조회
PUT    /api/database/connections/{id}/activate  # 연결 활성화
DELETE /api/database/connections/{id}       # 연결 삭제
```

### **쿼리 실행**
```http
POST   /api/database/query                  # SQL 쿼리 실행
GET    /api/database/schema                 # 스키마 정보 조회
GET    /api/database/schema/tables          # 테이블 목록
GET    /api/database/schema/tables/{name}   # 특정 테이블 정보
```

### **모니터링**
```http
GET    /api/database/status                 # 시스템 상태
GET    /api/database/health                 # 헬스 체크
GET    /api/database/history                # 연결 히스토리
```

---

## 🔧 **환경 변수**

```env
# .env 파일
KOSIS_OPEN_API_KEY=your_kosis_api_key_here

# 선택적 설정
OPENAI_API_KEY=your_openai_key          # AI 기능용
DATABASE_URL=postgresql://...           # 기본 DB 연결
LOG_LEVEL=INFO                          # 로그 레벨
```

---

## 📁 **프로젝트 구조**

```
text2sqlagent/
├── backend/                 # FastAPI 백엔드
│   ├── database/           # 데이터베이스 레이어
│   │   ├── handlers/      # 각 DB별 핸들러
│   │   │   ├── base_handler.py
│   │   │   ├── mysql_handler.py
│   │   │   ├── postgresql_handler.py
│   │   │   ├── mongodb_handler.py
│   │   │   ├── sqlite_handler.py
│   │   │   ├── api_handler.py      # API 베이스 핸들러
│   │   │   ├── kosis_handler.py    # KOSIS API 핸들러
│   │   │   └── handler_factory.py  # 핸들러 팩토리
│   │   └── connection_manager.py   # 연결 관리자
│   ├── api/                # REST API 레이어
│   │   └── database_api.py # API 엔드포인트
│   └── main.py            # FastAPI 메인 앱
├── frontend/               # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/
│   │   │   ├── ide/       # IDE 페이지
│   │   │   └── page.tsx   # 홈 페이지
│   │   ├── components/
│   │   │   ├── ide/       # IDE 컴포넌트들
│   │   │   └── chat/      # 채팅 UI
│   │   ├── types/         # TypeScript 타입
│   │   └── utils/         # 유틸리티 함수
│   └── package.json
├── requirements.txt        # Python 의존성
├── .env.example           # 환경 변수 템플릿
└── README.md              # 이 파일
```

---

## 🛠️ **기술 스택**

### **백엔드**
- **FastAPI**: 고성능 Python 웹 프레임워크
- **AsyncIO**: 비동기 프로그래밍
- **Pydantic**: 데이터 검증 및 직렬화
- **aiohttp**: 비동기 HTTP 클라이언트

### **데이터베이스 드라이버**
- **aiomysql**: MySQL 비동기 드라이버
- **asyncpg**: PostgreSQL 고성능 드라이버
- **motor**: MongoDB 비동기 드라이버
- **aiosqlite**: SQLite 비동기 드라이버

### **프론트엔드**
- **Next.js 14**: React 기반 풀스택 프레임워크
- **TypeScript**: 정적 타입 검사
- **Tailwind CSS**: 유틸리티 우선 CSS
- **Shadcn/ui**: 고품질 React 컴포넌트

---

## 🎯 **로드맵**

### **Phase 1: 기본 시스템 (완료 ✅)**
- ✅ 다중 데이터베이스 핸들러 시스템
- ✅ KOSIS API 통합
- ✅ IDE 스타일 프론트엔드
- ✅ 실시간 연결 관리

### **Phase 2: AI 기능 강화 (진행 중 🔄)**
- 🔄 자연어 → SQL 변환 고도화
- 🔄 쿼리 최적화 제안
- 🔄 데이터 인사이트 자동 생성
- 🔄 대화형 데이터 분석

### **Phase 3: 확장 및 고도화 (계획 📋)**
- 📋 추가 API 통합 (Google Sheets, Notion, GitHub)
- 📋 데이터 파이프라인 구축
- 📋 실시간 협업 기능
- 📋 클라우드 배포 자동화

---

## 🤝 **기여하기**

1. **Fork** 프로젝트
2. **Feature Branch** 생성 (`git checkout -b feature/amazing-feature`)
3. **Commit** 변경사항 (`git commit -m 'Add amazing feature'`)
4. **Push** to Branch (`git push origin feature/amazing-feature`)
5. **Pull Request** 오픈

---

## 📄 **라이센스**

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 확인하세요.

---

## 🙋‍♂️ **지원**

- **문서**: [MINDSDB_INTEGRATION.md](./MINDSDB_INTEGRATION.md)
- **이슈**: GitHub Issues에서 버그 리포트 및 기능 요청
- **이메일**: [이메일 주소]

---

**🎯 MindsDB의 확장 가능한 아키텍처를 적용한 차세대 다중 데이터베이스 플랫폼** ✨ 