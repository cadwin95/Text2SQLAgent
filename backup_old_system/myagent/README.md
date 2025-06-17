# 🔗 MyAgent v2.0 - Plan-Execute-Reflect 아키텍처

> **MCP 기반 데이터 분석 에이전트 시스템**

## 🏗️ 새로운 아키텍처 개요

### 📋 디렉토리 구조
```
myagent/
├── mcp_server/          # MCP Server 도구 + 리소스 + 프롬프트
│   └── kosis_api.py     # KOSIS API 전용 MCP Server
│
├── agent/               # Plan-Execute-Reflect 에이전트들
│   ├── chain.py         # 🔗 전체 워크플로우 조율 (마스터)
│   ├── planner.py       # 🎯 계획 수립 전담
│   ├── executor.py      # ⚡ 실행 전담 (MCP 도구 호출)
│   ├── reflector.py     # 🔄 결과 분석 & 재계획 전담
│   └── sql_agent.py     # 🗃️ SQL 분석 엔진
│
├── server/
│   └── api_server.py    # 🖥️ FastAPI 서버 (integrated_api_server.py 역할)
│
├── utils/
│   └── llm_client.py    # 🤖 LLM 클라이언트 공용화
│
├── tests/               # 테스트 코드
│
├── mcp_config.json      # 📡 MCP Server 설정
└── README.md           # 📖 이 파일
```

## 🎯 핵심 컨셉: Plan-Execute-Reflect

### 1. **PLAN** (계획 수립)
- **담당**: `planner.py`
- **역할**: 사용자 질문 → 구조화된 실행 계획
- **출력**: JSON 형태의 단계별 액션 플랜

### 2. **EXECUTE** (실행)
- **담당**: `executor.py`
- **역할**: 계획된 단계들을 실제로 실행
- **기능**: MCP Server 호출 + SQL 분석 + 데이터 처리

### 3. **REFLECT** (반성)
- **담당**: `reflector.py`
- **역할**: 실행 결과 분석 + 품질 평가 + 재계획 생성
- **출력**: 개선된 재계획 또는 종료 판단

### 4. **CHAIN** (조율)
- **담당**: `chain.py`
- **역할**: Plan → Execute → Reflect 사이클 관리
- **특징**: 품질 기준 충족 시까지 반복

## 🚀 주요 개선사항

### ✅ **단일 책임 원칙**
- 각 모듈이 하나의 명확한 책임만 담당
- 코드 가독성 및 유지보수성 극대화

### ✅ **MCP Server 독립화** 
- `kosis_api.py`: 독립 실행 가능한 MCP Server
- `mcp_config.json`: 동적 MCP Server 연결 설정
- 시중 MCP 도구들과 자유로운 조합 가능

### ✅ **LLM 백엔드 통합**
- `llm_client.py`: OpenAI, HuggingFace, GGUF 지원
- 환경변수로 백엔드 동적 선택

### ✅ **적응적 품질 제어**
- 실행 결과 품질 자동 평가
- 기준 미달 시 자동 재계획 및 재실행
- 최대 반복 횟수 제한으로 무한 루프 방지

## 🔧 설치 및 실행

### 1. 의존성 설치
```bash
cd myagent
pip install fastapi uvicorn pandas sqlite3 openai transformers
pip install python-dotenv requests
```

### 2. 환경변수 설정
```bash
# .env 파일 생성
export LLM_BACKEND=openai
export OPENAI_API_KEY=your_key
export KOSIS_OPEN_API_KEY=your_kosis_key
export MAX_ITERATIONS=3
```

### 3. MCP Server 실행 (선택사항)
```bash
# KOSIS MCP Server 독립 실행
python mcp_server/kosis_api.py
```

### 4. API 서버 실행
```bash
# Chain과 연동된 API 서버
python server/api_server.py
```

## 📡 API 사용법

### OpenAI 호환 API
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "최근 5년간 인구 증가율을 분석해주세요"}
    ],
    "stream": false
  }'
```

### 상태 확인
```bash
# 서버 상태
curl http://localhost:8000/status

# 헬스 체크
curl http://localhost:8000/health

# 실행 요약
curl http://localhost:8000/execution-summary
```

## 🔄 실행 플로우 예시

```
1. 사용자: "인구 증가율 분석해줘"
   ↓
2. Planner: 
   - 질문 분석
   - MCP 도구 활용 계획 수립
   - SQL 분석 계획 포함
   ↓
3. Executor:
   - KOSIS MCP Server → 인구 데이터 수집
   - SQL Agent → 데이터 분석
   - 시각화 데이터 생성
   ↓
4. Reflector:
   - 결과 품질 평가 (0.85점)
   - 기준 충족 → 종료
   ↓
5. Chain: 최종 결과 반환
```

## 🎛️ 설정 가능한 옵션

### Chain 설정
- `MAX_ITERATIONS`: 최대 반복 횟수 (기본값: 3)
- `QUALITY_THRESHOLD`: 품질 기준점 (기본값: 0.7)

### LLM 설정
- `LLM_BACKEND`: openai, huggingface, gguf
- `OPENAI_MODEL`: gpt-3.5-turbo, gpt-4 등

### MCP 설정
- `mcp_config.json`에서 MCP Server 추가/제거
- 우선순위 및 자동 시작 설정

## 🧪 테스트

### 단위 테스트
```bash
# 개별 모듈 테스트
python -m pytest tests/test_planner.py
python -m pytest tests/test_executor.py
python -m pytest tests/test_reflector.py
```

### 통합 테스트
```bash
# 전체 Chain 테스트
python -m pytest tests/test_chain.py
```

### 수동 테스트
```bash
# Chain 직접 실행
cd agent
python chain.py
```

## 🔍 디버깅

### 로그 확인
```bash
# 실시간 로그
tail -f logs/myagent.log

# 레벨별 로그
export LOG_LEVEL=DEBUG
```

### 상태 확인
```bash
# Chain 상태
curl http://localhost:8000/status

# SQL Agent 테이블 정보
curl http://localhost:8000/tables
```

## 🚧 확장 방법

### 새로운 MCP Server 추가
1. `mcp_config.json`에 서버 정보 추가
2. `planner.py`에서 도구 인식 로직 업데이트
3. `executor.py`에서 실행 로직 추가

### 새로운 LLM 백엔드 추가
1. `utils/llm_client.py`에 새 클라이언트 클래스 추가
2. `get_llm_client()` 팩토리 함수 업데이트

### 새로운 분석 도구 추가
1. `agent/` 디렉토리에 새 모듈 추가
2. `executor.py`에서 호출 로직 통합

## 💡 모범 사례

### 1. **질문 작성 팁**
- 구체적이고 명확한 질문
- 시간 범위 명시 (예: "최근 5년간")
- 분석 목적 포함 (예: "비교", "트렌드")

### 2. **성능 최적화**
- 필요한 MCP Server만 활성화
- 적절한 품질 기준 설정
- 메모리 사용량 모니터링

### 3. **오류 처리**
- 로그 레벨을 DEBUG로 설정
- 단계별 실행 결과 확인
- MCP Server 연결 상태 확인

## 📈 향후 계획

- [ ] 웹 UI 개발
- [ ] 더 많은 MCP Server 연동
- [ ] 고급 시각화 도구 통합
- [ ] 성능 최적화
- [ ] 멀티 에이전트 협업

---

> **MyAgent v2.0** - Plan, Execute, Reflect의 지능적 순환으로 더 나은 분석을 제공합니다. 🚀 