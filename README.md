# 🤖 AI Assistant with MCP Integration

> **통합 AI 어시스턴트 - 일반 대화와 데이터 분석을 모두 지원하는 차세대 AI 시스템**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.0+-black.svg)](https://nextjs.org/)
[![MCP](https://img.shields.io/badge/MCP-Protocol-purple.svg)](https://modelcontextprotocol.io/)

## 🌟 주요 특징

### 🧠 **스마트 라우팅**
- **일반 대화**: "안녕하세요", "오늘 날씨 어때?", "지금 몇 시야?" → OpenAI GPT 직접 처리
- **데이터 분석**: "인구 통계 보여줘", "GDP 추이 분석해줘" → MCP를 통한 KOSIS 데이터 처리
- 질문 유형 자동 감지 및 최적 처리 경로 선택

### 🔗 **MCP (Model Context Protocol) 통합**
- 표준 MCP 프로토콜 기반 확장 가능한 아키텍처
- KOSIS (한국 통계청) 데이터 실시간 연동
- 다양한 MCP 서버 추가 가능

### 💬 **자연스러운 대화 경험**
- OpenAI GPT 기반 자연어 처리
- 한국어 최적화 및 이모지 지원
- 스트리밍 응답으로 빠른 반응성

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/yourusername/text2sqlagent.git
cd text2sqlagent

# 환경변수 설정 (.env 파일)
OPENAI_API_KEY=your_openai_api_key
KOSIS_OPEN_API_KEY=your_kosis_api_key  # 선택사항
```

### 2. 시스템 실행

```bash
# 통합 실행 스크립트
python start_system.py
```

### 3. 웹 인터페이스 접속

- Frontend: http://localhost:3000
- API 문서: http://localhost:8000/docs

## 🏗️ 시스템 구조

```
text2sqlagent/
├── api_server.py          # 🌐 통합 API 서버 (FastAPI)
├── start_system.py        # 🚀 시스템 시작 스크립트
│
├── mcp_client/           # 🔌 MCP 클라이언트
│   └── client.py         # MCP 프로토콜 구현
│
├── mcp_servers/          # 📊 MCP 서버들
│   └── kosis_server/     # KOSIS 데이터 서버
│       ├── server.py
│       └── tools.py
│
├── frontend/             # 🎨 웹 인터페이스 (Next.js)
│   └── src/
│       ├── components/   # React 컴포넌트
│       └── app/         # Next.js 앱
│
└── backup_old_system/    # 📦 이전 버전 백업
```

## 💡 사용 예시

### 일반 대화
```
👤: 안녕하세요!
🤖: 안녕하세요! 반갑습니다 😊 무엇을 도와드릴까요?

👤: 오늘 몇 시야?
🤖: 현재 시각은 2024년 12월 15일 오후 3시 45분입니다 ⏰

👤: 인공지능이 뭐야?
🤖: 인공지능(AI)은 인간의 지능을 모방한 컴퓨터 시스템입니다...
```

### 데이터 분석
```
👤: 최근 5년간 한국 인구 추이를 보여줘
🤖: 📊 KOSIS 데이터를 조회하고 있습니다...
    [인구 통계 데이터 및 분석 결과 표시]

👤: GDP 성장률 분석해줘
🤖: 📈 경제 지표를 분석하겠습니다...
    [GDP 데이터 및 트렌드 분석 표시]
```

## 🛠️ 개발자 가이드

### API 엔드포인트

#### 채팅 완료 (OpenAI 호환)
```http
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "user", "content": "안녕하세요"}
  ],
  "stream": false
}
```

#### 헬스 체크
```http
GET /health
```

#### MCP 도구 목록
```http
GET /tools
```

### MCP 서버 추가하기

1. `mcp_servers/` 디렉토리에 새 서버 생성
2. MCP 프로토콜에 맞춰 도구 구현
3. `api_server.py`의 `lifespan` 함수에서 서버 등록

```python
# 새로운 MCP 서버 추가 예시
new_config = MCPServerConfig(
    name="my_server",
    command="python",
    args=["mcp_servers/my_server/server.py"]
)
await mcp_client.add_server(new_config)
```

## 📋 요구사항

- Python 3.8+
- Node.js 16+
- OpenAI API 키 (필수)
- KOSIS API 키 (선택, 데이터 분석용)

## 🤝 기여하기

1. Fork 저장소
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치 푸시 (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

- [OpenAI](https://openai.com) - GPT 모델 제공
- [Anthropic](https://anthropic.com) - MCP 프로토콜 개발
- [KOSIS](https://kosis.kr) - 한국 통계 데이터 제공

---

<p align="center">Made with ❤️ by AI Assistant Team</p> 