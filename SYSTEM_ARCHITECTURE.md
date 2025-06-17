# 🚀 통합 AI Assistant 시스템 아키텍처 v3.0

## 📋 시스템 개요

이 프로젝트는 **일반 대화**와 **데이터 분석**을 모두 지원하는 통합 AI Assistant 시스템입니다.
Model Context Protocol (MCP) 표준을 준수하며, OpenAI GPT와 KOSIS 통계 데이터를 연동합니다.

## 🏗️ 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                          │
│                    http://localhost:3000                        │
│                                                                 │
│  📱 React Components:                                           │
│  ├── ChatContainer (메인 채팅 UI)                               │
│  ├── MessageList (메시지 표시)                                   │
│  ├── MessageInput (사용자 입력)                                  │
│  └── ChartDisplay (데이터 시각화)                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP API Calls (/v1/chat/completions)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              통합 API 서버 (FastAPI)                           │
│                  http://localhost:8000                          │
│                                                                 │
│  🧠 Smart Router:                                               │
│  ├── QuestionAnalyzer (질문 유형 분석)                          │
│  ├── General Chat → OpenAI API                                 │
│  ├── Data Analysis → MCP Client                                │
│  └── Fallback System (연결 실패시)                              │
│                                                                 │
│  🔌 MCP Client:                                                 │
│  ├── 표준 MCP 프로토콜 구현                                      │
│  ├── JSON-RPC 2.0 통신                                         │
│  └── stdio 기반 서버 연결                                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ stdio/JSON-RPC
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│         KOSIS MCP Server (FastMCP)                              │
│     mcp_servers/kosis_server/server.py                         │
│                                                                 │
│  🛠️ Tools (도구):                                               │
│  ├── fetch_statistics_data (통계 데이터 조회)                   │
│  ├── search_statistics (통계 검색)                              │
│  └── list_statistics (통계 목록)                                │
│                                                                 │
│  📁 Resources (리소스):                                         │
│  ├── statistics://metadata/{tblId}                             │
│  └── statistics://explanation/{statId}                         │
│                                                                 │
│  💬 Prompts (프롬프트):                                         │
│  ├── analyze_population_trend                                  │
│  └── compare_economic_indicators                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS API
                      ▼
                   ┌─────────────────────┐
                   │   KOSIS Open API    │
                   │   (통계청 공식 API)  │
                   │   kosis.kr/openapi  │
                   └─────────────────────┘
```

## 📦 핵심 컴포넌트

### 1. Frontend (Next.js + React + TypeScript)
- **위치**: `frontend/`
- **포트**: 3000
- **주요 기능**:
  - 반응형 채팅 UI
  - 실시간 스트리밍 응답
  - 차트/테이블 데이터 시각화
  - TypeScript 타입 안정성

### 2. 통합 API 서버 (FastAPI + Python)
- **위치**: `api_server.py`
- **포트**: 8000
- **주요 기능**:
  - OpenAI 호환 API 엔드포인트
  - 스마트 질문 라우팅
  - MCP Client 관리
  - Fallback 시스템

### 3. MCP Client
- **위치**: `mcp_client/`
- **주요 기능**:
  - MCP 표준 프로토콜 구현
  - 다중 서버 연결 관리
  - JSON-RPC 2.0 통신
  - 비동기 도구 호출

### 4. KOSIS MCP Server
- **위치**: `mcp_servers/kosis_server/`
- **주요 기능**:
  - FastMCP 프레임워크 사용
  - KOSIS API 래핑
  - 통계 데이터 도구 제공
  - 분석 템플릿 프롬프트

### 5. Fallback 시스템
- **위치**: `kosis_fallback.py`
- **주요 기능**:
  - MCP 연결 실패시 대체 동작
  - 모의 통계 데이터 제공
  - 시스템 견고성 보장

## 🎯 데이터 플로우

### 일반 대화 플로우
```
1. 사용자 질문 → Frontend
2. API 서버에서 질문 분석 (일반 대화로 분류)
3. OpenAI API 직접 호출
4. 응답을 Frontend로 스트리밍
```

### 데이터 분석 플로우
```
1. 사용자 질문 → Frontend
2. API 서버에서 질문 분석 (데이터 분석으로 분류)
3. MCP Client를 통해 KOSIS 서버 연결
4. KOSIS 도구 실행 → 통계청 API 호출
5. 데이터 처리 후 Frontend로 응답
```

### Fallback 플로우
```
1. MCP 서버 연결 실패 감지
2. kosis_fallback.py에서 모의 데이터 생성
3. 실제 API와 유사한 형식으로 응답
4. 사용자에게 대체 정보 제공
```

## 🔧 기술 스택

### Backend
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Python 3.8+**: 비동기 프로그래밍
- **MCP SDK**: Model Context Protocol 표준 구현
- **FastMCP**: MCP 서버 구축 프레임워크
- **OpenAI SDK**: GPT 모델 연동
- **Uvicorn**: ASGI 서버

### Frontend
- **Next.js 14**: React 풀스택 프레임워크
- **TypeScript**: 타입 안정성
- **Tailwind CSS**: 유틸리티 CSS 프레임워크
- **Zustand**: 경량 상태 관리
- **Chart.js**: 데이터 시각화

### Data & API
- **KOSIS Open API**: 한국 통계청 공식 데이터
- **OpenAI GPT**: 언어 모델
- **JSON-RPC 2.0**: MCP 통신 프로토콜
- **WebSocket**: 실시간 스트리밍 (선택사항)

## 🚀 실행 방법

### 1. 환경 설정
```bash
# 환경변수 설정 (.env 파일)
OPENAI_API_KEY=your_openai_api_key
KOSIS_OPEN_API_KEY=your_kosis_api_key
```

### 2. 자동 실행 (권장)
```bash
python start_system.py
```

### 3. 수동 실행
```bash
# 1. API 서버 시작
python api_server.py

# 2. Frontend 서버 시작 (별도 터미널)
cd frontend
npm run dev
```

### 4. 접속
- Frontend: http://localhost:3000
- API 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs

## 📁 디렉토리 구조

```
text2sqlagent/
├── 🚀 start_system.py           # 통합 시작 스크립트
├── 🌐 api_server.py             # 메인 API 서버
├── 🔄 kosis_fallback.py         # Fallback 시스템
│
├── 📱 frontend/                 # Next.js Frontend
│   ├── src/
│   │   ├── app/                 # Next.js 앱 라우터
│   │   ├── components/          # React 컴포넌트
│   │   ├── hooks/               # React 훅
│   │   ├── types/               # TypeScript 타입
│   │   └── utils/               # 유틸리티 함수
│   ├── package.json
│   └── next.config.js
│
├── 🔌 mcp_client/               # MCP 클라이언트
│   ├── __init__.py
│   └── client.py                # MCP 표준 클라이언트 구현
│
├── 🗃️ mcp_servers/             # MCP 서버들
│   └── kosis_server/            # KOSIS 통계 서버
│       ├── server.py            # FastMCP 서버
│       ├── tools.py             # KOSIS API 도구
│       └── __init__.py
│
├── 🗂️ backup_old_system/       # 이전 시스템 백업
│   ├── application/
│   ├── backend/
│   └── myagent/
│
├── 📋 requirements.txt          # Python 의존성
├── 📦 pyproject.toml           # 프로젝트 설정
└── 📖 README.md                # 프로젝트 설명
```

## 🔐 보안 및 환경변수

### 필수 환경변수
- `OPENAI_API_KEY`: OpenAI API 인증 키
- `KOSIS_OPEN_API_KEY`: KOSIS 통계청 API 키

### 선택적 환경변수
- `PORT`: API 서버 포트 (기본값: 8000)
- `HOST`: API 서버 호스트 (기본값: 0.0.0.0)

## 🐛 디버깅 및 로그

### 로그 확인
```bash
# API 서버 로그 (터미널 출력)
python api_server.py

# MCP 서버 개별 실행 (디버깅용)
cd mcp_servers/kosis_server
python server.py
```

### 상태 확인
- Health Check: http://localhost:8000/health
- MCP 도구 목록: http://localhost:8000/tools

## 🔧 개발 가이드

### 새로운 MCP 도구 추가
1. `mcp_servers/kosis_server/tools.py`에 함수 추가
2. `server.py`에 `@mcp.tool()` 데코레이터로 등록
3. API 서버 재시작

### Frontend 컴포넌트 추가
1. `frontend/src/components/`에 컴포넌트 생성
2. `types/index.ts`에 타입 정의 추가
3. 필요시 `hooks/`에 커스텀 훅 생성

### API 엔드포인트 추가
1. `api_server.py`에 FastAPI 라우터 추가
2. `frontend/src/utils/api.ts`에 클라이언트 함수 추가

## 📊 모니터링 및 메트릭

### 성능 지표
- API 응답 시간
- MCP 도구 실행 시간
- 스트리밍 응답 지연시간
- 오류율 및 성공률

### 사용 통계
- 일반 대화 vs 데이터 분석 비율
- 인기 KOSIS 도구 사용량
- 세션 길이 및 메시지 수

## 🔮 향후 계획

### 단기 개선사항
- [ ] WebSocket 기반 실시간 통신 구현
- [ ] 사용자 인증 및 세션 관리
- [ ] 차트 시각화 개선
- [ ] 모바일 반응형 최적화

### 장기 로드맵
- [ ] 다중 데이터 소스 연동 (공공데이터포털, 금융감독원 등)
- [ ] AI 에이전트 워크플로우 구현
- [ ] 협업 기능 및 공유 채팅
- [ ] 플러그인 시스템 구축

---

## 📞 지원 및 문의

- **프로젝트**: 통합 AI Assistant v3.0
- **MCP 버전**: 1.0 (2024년 11월 Anthropic 표준)
- **문서 업데이트**: 2024년 11월

이 시스템은 MCP 표준을 완전히 준수하며, 확장 가능하고 유지보수가 용이한 구조로 설계되었습니다. 