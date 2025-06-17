# 🤖 AI Assistant 통합 시스템 가이드

## 📋 시스템 개요

이 시스템은 **일반 대화**와 **데이터 분석**을 모두 처리할 수 있는 통합 AI 어시스턴트입니다.

### 핵심 특징
- 🧠 **스마트 라우팅**: 질문 유형을 자동으로 감지하여 적절한 처리 방식 선택
- 💬 **일반 대화**: OpenAI GPT를 직접 사용하여 자연스러운 대화
- 📊 **데이터 분석**: MCP를 통해 KOSIS 통계청 데이터 실시간 조회 및 분석

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
OPENAI_API_KEY=your_openai_api_key       # 필수
KOSIS_OPEN_API_KEY=your_kosis_api_key    # 선택 (데이터 분석용)
```

### 2. 시스템 실행

```bash
# 통합 실행 스크립트
python start_system.py

# 또는 개별 실행
python api_server.py        # API 서버만
cd frontend && npm run dev  # Frontend만
```

### 3. 사용하기

웹 브라우저에서 http://localhost:3000 접속

## 💡 질문 예시

### 일반 대화 (OpenAI 직접 처리)
```
👤: 안녕하세요!
👤: 오늘 몇 시야?
👤: 날씨가 어때?
👤: 인공지능에 대해 설명해줘
👤: 파이썬 코드 작성 도와줘
```

### 데이터 분석 (MCP 도구 사용)
```
👤: 최근 5년간 인구 통계 보여줘
👤: 서울시 인구 변화 분석해줘
👤: GDP 성장률 추이를 알려줘
👤: 통계청 데이터 검색해줘
```

## 🏗️ 아키텍처

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│  API Server  │────▶│   OpenAI    │
│  (Next.js)  │     │  (FastAPI)   │     │     GPT     │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ MCP Client   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ KOSIS MCP    │
                    │   Server     │
                    └──────────────┘
```

## 🔍 질문 분석 로직

시스템은 다음과 같은 방식으로 질문을 분석합니다:

### 1. 키워드 기반 분석
```python
# 데이터 관련 키워드
data_keywords = [
    "통계", "데이터", "분석", "조회", "검색",
    "인구", "경제", "GDP", "물가", "고용",
    "KOSIS", "통계청", "자료", "수치"
]

# 일반 대화 패턴
general_patterns = [
    "안녕", "감사", "고마워", "뭐야", "누구야",
    "시간", "날짜", "오늘", "내일", "어제"
]
```

### 2. 특별 처리
- 시간/날짜 질문: 현재 시각 정보 추가
- 데이터 분석: MCP 도구 호출 계획 수립

## 🛠️ 개발자 가이드

### API 엔드포인트

#### 1. 채팅 완료 (OpenAI 호환)
```bash
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "user", "content": "질문"}
  ],
  "stream": false  # true로 설정하면 스트리밍
}
```

#### 2. 헬스 체크
```bash
GET /health

응답:
{
  "status": "healthy",
  "openai": true,
  "mcp_servers": [...]
}
```

#### 3. MCP 도구 목록
```bash
GET /tools

응답:
{
  "tools": [...],
  "resources": [...],
  "prompts": [...]
}
```

### MCP 도구 추가하기

1. 새 MCP 서버 생성
```python
# mcp_servers/my_server/server.py
from fastmcp import FastMCP

mcp = FastMCP("My-Server")

@mcp.tool()
def my_tool(param1: str) -> dict:
    """도구 설명"""
    return {"result": "data"}

if __name__ == "__main__":
    mcp.run()
```

2. API 서버에 등록
```python
# api_server.py의 lifespan 함수에 추가
my_config = MCPServerConfig(
    name="my_server",
    command="python",
    args=["mcp_servers/my_server/server.py"]
)
await mcp_client.add_server(my_config)
```

## 🔧 문제 해결

### KOSIS API 키 없음
- 증상: 데이터 분석 시 오류 발생
- 해결: [KOSIS OpenAPI](https://kosis.kr/openapi) 에서 키 발급 후 .env 파일에 추가

### OpenAI API 오류
- 증상: 모든 질문에 대해 오류 발생
- 해결: OpenAI API 키 확인, 사용량 한도 확인

### MCP 서버 연결 실패
- 증상: 헬스 체크에서 MCP 서버가 보이지 않음
- 해결: Python 환경 확인, mcp 패키지 설치 확인

## 📈 성능 최적화

### 1. 응답 속도 개선
- OpenAI 모델을 `gpt-3.5-turbo`로 사용 (gpt-4보다 빠름)
- 스트리밍 응답 활용으로 체감 속도 향상

### 2. 데이터 캐싱
- 자주 조회되는 KOSIS 데이터는 캐싱 고려
- Redis 또는 메모리 캐시 구현 가능

### 3. 동시 요청 처리
- FastAPI의 비동기 처리로 다수 사용자 동시 처리
- 필요시 워커 프로세스 증가

## 🚀 배포 가이드

### Docker 사용
```dockerfile
FROM python:3.9

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN cd frontend && npm install && npm run build

CMD ["python", "start_system.py"]
```

### 프로덕션 설정
- Nginx 리버스 프록시 설정
- SSL 인증서 적용
- 환경변수 보안 관리
- 로그 모니터링 설정

## 📚 참고 자료

- [OpenAI API 문서](https://platform.openai.com/docs)
- [MCP 프로토콜](https://modelcontextprotocol.io/)
- [KOSIS OpenAPI](https://kosis.kr/openapi)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Next.js 문서](https://nextjs.org/docs) 