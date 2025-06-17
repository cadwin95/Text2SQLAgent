# Text2SQL MCP System 설치 및 실행 가이드

## 🚀 빠른 시작

### 1. 환경 설정

`.env` 파일을 프로젝트 루트에 생성하고 다음 내용을 추가하세요:

```env
# KOSIS API 키 (https://kosis.kr/openapi 에서 발급)
KOSIS_OPEN_API_KEY=your_kosis_api_key_here

# OpenAI API 키
OPENAI_API_KEY=your_openai_api_key_here

# 사용할 OpenAI 모델 (선택사항)
OPENAI_MODEL=gpt-3.5-turbo
```

### 2. Frontend 환경 설정

`frontend/.env.local` 파일을 생성하고 다음 내용을 추가하세요:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Text2SQL MCP System
NEXT_PUBLIC_APP_VERSION=2.0.0
```

### 3. 의존성 설치

```bash
# Python 패키지 설치
pip install -r requirements.txt

# Frontend 패키지 설치
cd frontend
npm install
cd ..
```

### 4. 시스템 시작

#### 방법 1: 통합 실행 스크립트 사용 (권장)

```bash
python start_system.py
```

#### 방법 2: 개별 실행

```bash
# Terminal 1: Backend API 서버
python backend/integrated_api_server.py

# Terminal 2: Frontend 개발 서버
cd frontend
npm run dev
```

## 📋 시스템 구성

### MCP 아키텍처

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│   Frontend      │────▶│  Backend API     │────▶│  MCP Client   │
│  (Next.js)      │     │  (FastAPI)       │     │  Application  │
└─────────────────┘     └──────────────────┘     └───────────────┘
                                                          │
                                                          ▼
                                                  ┌───────────────┐
                                                  │  MCP Server   │
                                                  │  (KOSIS)      │
                                                  └───────────────┘
                                                          │
                                                          ▼
                                                  ┌───────────────┐
                                                  │  KOSIS API    │
                                                  └───────────────┘
```

### 주요 컴포넌트

1. **Frontend (포트 3000)**
   - Next.js 기반 웹 UI
   - 실시간 채팅 인터페이스
   - 데이터 시각화 (차트, 테이블)

2. **Backend API (포트 8000)**
   - FastAPI 기반 REST API
   - OpenAI 호환 API 제공
   - 스트리밍 응답 지원

3. **MCP Client Application**
   - LLM 관리 (OpenAI, HuggingFace 등)
   - MCP 서버들과의 통신
   - Agent 오케스트레이션

4. **MCP Server (KOSIS)**
   - KOSIS API 래핑
   - 통계 데이터 조회 도구 제공
   - 표준 MCP 프로토콜 지원

## 🛠️ 주요 기능

### 1. 자연어 → SQL 변환
- 한국어 질의 이해
- 적절한 통계 데이터 자동 검색
- SQL 쿼리 생성 및 실행

### 2. KOSIS 통계 데이터 연동
- 인구, 경제, 사회 통계 조회
- 시계열 데이터 분석
- 지역별 비교 분석

### 3. 데이터 시각화
- 실시간 차트 생성
- 테이블 형태 데이터 표시
- 분석 결과 요약

### 4. MCP 기반 확장성
- 새로운 데이터 소스 쉽게 추가
- 표준 프로토콜로 호환성 확보
- 독립적인 서버 운영

## 🔍 문제 해결

### 1. KOSIS API 키 오류
```
KOSIS_API_KEY not set. Some features may not work.
```
→ `.env` 파일에 `KOSIS_OPEN_API_KEY` 설정 확인

### 2. MCP Client 연결 실패
```
Failed to connect to kosis
```
→ Python 환경에서 필요한 패키지 설치 확인:
```bash
pip install mcp fastmcp python-dotenv
```

### 3. Frontend 빌드 오류
→ Node.js 버전 확인 (16.x 이상 권장)
```bash
node --version
npm --version
```

### 4. Backend API 오류
→ 로그 확인:
```bash
# Backend 로그
tail -f backend.log

# Frontend 콘솔
브라우저 개발자 도구 → Console
```

## 📊 사용 예제

### 기본 질의
- "2023년 서울시 인구 통계를 보여주세요"
- "최근 5년간 한국 GDP 성장률을 보여주세요"
- "시도별 인구 분포를 분석해주세요"

### 고급 분석
- "서울과 부산의 인구 변화를 비교 분석해주세요"
- "경제활동인구와 실업률의 상관관계를 분석해주세요"
- "지역별 고령화 지수를 시각화해주세요"

## 🔧 개발자 가이드

### 새로운 MCP 서버 추가
1. `mcp_servers/` 디렉토리에 새 서버 생성
2. `mcp_servers/config/servers.json`에 설정 추가
3. MCP Client에서 자동으로 인식

### API 엔드포인트
- `GET /` - 서버 상태 확인
- `POST /v1/chat/completions` - 채팅 완료 API
- `POST /v1/chat/stream` - 스트리밍 채팅 API
- `GET /agent/status` - Agent 상태 확인

### 로깅 설정
```python
# 로그 레벨 조정
logging.basicConfig(level=logging.DEBUG)
```

## 📝 라이선스

MIT License

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 