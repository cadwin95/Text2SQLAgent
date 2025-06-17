# MCP 기반 Text2SQL Agent 시스템

## 🎯 개요

표준 **Model Context Protocol (MCP)**을 구현한 Text2SQL Agent 시스템입니다. 
- **MCP 서버**: KOSIS 등 공공데이터 API를 MCP 도구로 제공
- **MCP 클라이언트**: 여러 MCP 서버와 동시 연결 관리
- **LLM 통합**: OpenAI, HuggingFace, GGUF 등 다양한 모델 지원
- **표준 호환**: Cursor, Claude Desktop 등과 호환 가능

## 🏗️ 시스템 구조

```
project/
├── mcp_servers/              # MCP 서버들
│   ├── kosis_server/        # KOSIS API MCP 서버
│   │   ├── server.py        # FastMCP 서버 구현
│   │   └── tools.py         # KOSIS API 함수들
│   └── config/
│       └── servers.json     # 서버 설정
│
├── mcp_client/              # MCP 클라이언트
│   └── client.py           # 표준 MCP 클라이언트
│
├── application/             # 애플리케이션 레이어
│   ├── main.py             # 메인 애플리케이션
│   ├── llm/                # LLM 매니저
│   │   └── manager.py      # 다중 LLM 백엔드 지원
│   └── agent/              # Agent 시스템
│       └── orchestrator.py # LLM-MCP 조율
│
└── mcp_architecture.md      # 아키텍처 설계 문서
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 필수 패키지 설치
pip install fastmcp mcp openai pandas

# 환경 변수 설정
export OPENAI_API_KEY="your-api-key"
export KOSIS_API_KEY="your-kosis-key"
export LLM_BACKEND="openai"  # openai, huggingface, gguf
```

### 2. KOSIS MCP 서버 실행

```bash
# 독립 실행 (테스트용)
python mcp_servers/kosis_server/server.py

# 출력 예시:
# Starting KOSIS Statistical Data Server
# Available tools: 3
# Available resources: 2
# Available prompts: 2
```

### 3. 통합 애플리케이션 실행

```bash
python application/main.py

# 출력 예시:
# === Application Status ===
# {
#   "llm": {"backend": "openai", "ready": true},
#   "mcp_servers": [{"name": "kosis", "connected": true, "tools": 3}],
#   "tools": 3,
#   "agent_ready": true
# }
```

## 🔧 MCP 서버 개발

### 새로운 MCP 서버 추가

```python
# mcp_servers/custom_server/server.py
from fastmcp import FastMCP

mcp = FastMCP("Custom Server")

@mcp.tool()
def custom_function(param: str) -> str:
    """커스텀 도구"""
    return f"Result: {param}"

@mcp.resource("custom://data")
def get_custom_data() -> str:
    """커스텀 리소스"""
    return "Custom data"

if __name__ == "__main__":
    mcp.run()
```

### 서버 설정 추가

```json
// mcp_servers/config/servers.json
{
  "servers": [
    {
      "name": "custom",
      "command": "python",
      "args": ["mcp_servers/custom_server/server.py"],
      "enabled": true
    }
  ]
}
```

## 🤝 Cursor 연동

### 1. Cursor 설정 파일 생성

```json
// .cursor/mcp_settings.json
{
  "mcpServers": {
    "kosis": {
      "command": "python",
      "args": ["mcp_servers/kosis_server/server.py"],
      "env": {
        "KOSIS_API_KEY": "your-key"
      }
    }
  }
}
```

### 2. Cursor에서 사용

```
// Cursor 채팅창에서
@kosis 2023년 서울시 인구 통계를 조회해주세요
```

## 📡 API 사용법

### Python에서 직접 사용

```python
import asyncio
from mcp_client.client import MCPClient, MCPServerConfig

async def main():
    # 클라이언트 생성
    client = MCPClient()
    
    # KOSIS 서버 연결
    config = MCPServerConfig(
        name="kosis",
        command="python",
        args=["mcp_servers/kosis_server/server.py"]
    )
    await client.add_server(config)
    
    # 도구 목록 조회
    tools = client.list_all_tools()
    print(f"Available tools: {tools}")
    
    # 도구 실행
    result = await client.call_tool(
        server_name="kosis",
        tool_name="fetch_statistics_data",
        arguments={
            "orgId": "101",
            "tblId": "DT_1B040A3",
            "startPrdDe": "2023",
            "endPrdDe": "2023"
        }
    )
    print(f"Result: {result}")

asyncio.run(main())
```

### REST API 서버 (계획)

```python
# application/api/server.py
from fastapi import FastAPI
from application.main import MCPApplication

app = FastAPI()
mcp_app = MCPApplication()

@app.post("/query")
async def process_query(query: str):
    result = await mcp_app.process_query(query)
    return result
```

## 🔄 LLM 백엔드 전환

### OpenAI (기본)

```bash
export LLM_BACKEND="openai"
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-3.5-turbo"
```

### HuggingFace (구현 예정)

```bash
export LLM_BACKEND="huggingface"
export HF_MODEL="microsoft/DialoGPT-medium"
```

### GGUF/llama.cpp (구현 예정)

```bash
export LLM_BACKEND="gguf"
export GGUF_MODEL_PATH="./models/llama-2-7b.gguf"
```

## 📊 주요 기능

### 1. 표준 MCP 프로토콜
- JSON-RPC 2.0 기반 통신
- stdio/SSE 전송 지원
- 도구, 리소스, 프롬프트 표준 구현

### 2. 다중 서버 관리
- 동시에 여러 MCP 서버 연결
- 동적 서버 추가/제거
- 서버별 상태 모니터링

### 3. LLM 통합
- 다양한 LLM 백엔드 지원
- MCP 도구 인식 프롬프트 자동 생성
- 스트리밍 응답 지원

### 4. 확장성
- 새로운 MCP 서버 쉽게 추가
- 커스텀 도구 개발 간편
- 외부 MCP 서버 연동 가능

## 🚧 로드맵

- [ ] SSE 전송 구현
- [ ] HuggingFace/GGUF 백엔드 완성
- [ ] FastAPI 기반 REST API
- [ ] WebSocket 실시간 통신
- [ ] MCP Registry 연동
- [ ] Docker 컨테이너화
- [ ] 프론트엔드 UI

## 🤝 기여하기

1. 새로운 MCP 서버 개발
2. LLM 백엔드 추가
3. 도구/리소스 확장
4. 문서화 개선

## 📚 참고 자료

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [KOSIS OpenAPI](https://kosis.kr/openapi)
- [Anthropic MCP](https://www.anthropic.com/news/model-context-protocol) 