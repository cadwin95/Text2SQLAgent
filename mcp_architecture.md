# MCP 서버-클라이언트 아키텍처 설계

## 🎯 목표
- **표준 MCP 프로토콜** 구현 (JSON-RPC 2.0)
- **다중 MCP 서버** 동시 연결 지원
- **Cursor 및 외부 도구** 호환성
- **다양한 LLM 백엔드** 지원

## 🏗️ 아키텍처 구성

### 1. MCP 서버 레이어
```
mcp_servers/
├── kosis_server/           # KOSIS API MCP 서버
│   ├── server.py          # FastMCP 기반 구현
│   ├── tools.py           # 도구 정의
│   ├── resources.py       # 리소스 정의
│   └── prompts.py         # 프롬프트 템플릿
├── custom_server/         # 커스텀 MCP 서버 예제
└── config/               # 서버 설정 파일
    └── servers.json      # 서버 목록 및 설정
```

### 2. MCP 클라이언트 레이어
```
mcp_client/
├── client.py             # MCP 클라이언트 구현
├── transport/           # 통신 레이어
│   ├── stdio.py        # stdio 통신
│   └── sse.py          # SSE 통신
├── registry.py          # 서버 레지스트리
└── manager.py           # 서버 생명주기 관리
```

### 3. 애플리케이션 레이어
```
application/
├── llm/                 # LLM 추상화
│   ├── base.py         # 공통 인터페이스
│   ├── openai.py       # OpenAI 구현
│   ├── huggingface.py  # HuggingFace 구현
│   └── gguf.py         # GGUF 구현
├── agent/              # 에이전트 시스템
│   ├── planner.py      # 계획 수립
│   ├── executor.py     # MCP 도구 실행
│   └── reflector.py    # 결과 평가
└── api/                # API 서버
    └── server.py       # FastAPI 서버
```

## 📡 통신 프로토콜

### JSON-RPC 2.0 메시지 형식
```json
// Request
{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
        "name": "fetch_kosis_data",
        "arguments": {
            "orgId": "101",
            "tblId": "DT_1B040A3"
        }
    }
}

// Response
{
    "jsonrpc": "2.0",
    "id": "1",
    "result": {
        "content": [
            {
                "type": "text",
                "text": "조회 결과..."
            }
        ]
    }
}
```

## 🔄 생명주기

### 1. 초기화
```python
# 서버 시작
server = KOSISMCPServer()
server.run()  # stdio로 실행

# 클라이언트 연결
client = MCPClient()
await client.connect_stdio("python", ["mcp_servers/kosis_server/server.py"])
await client.initialize()
```

### 2. 도구 검색 및 실행
```python
# 도구 목록 조회
tools = await client.list_tools()

# 도구 실행
result = await client.call_tool(
    "fetch_kosis_data",
    {"orgId": "101", "tblId": "DT_1B040A3"}
)
```

### 3. 종료
```python
await client.close()
```

## 🔧 구현 우선순위

1. **Phase 1: 핵심 MCP 구현**
   - [ ] KOSIS MCP 서버 (FastMCP)
   - [ ] 기본 MCP 클라이언트
   - [ ] stdio 통신 구현

2. **Phase 2: 통합 및 확장**
   - [ ] 다중 서버 관리
   - [ ] SSE 통신 추가
   - [ ] 외부 MCP 서버 연동

3. **Phase 3: 애플리케이션 통합**
   - [ ] Agent Chain 연동
   - [ ] LLM 추상화 완성
   - [ ] API 서버 통합

## 🚀 기대 효과

1. **표준 호환성**: Cursor, Claude Desktop 등과 호환
2. **확장성**: 새로운 MCP 서버 쉽게 추가
3. **유연성**: 다양한 LLM 백엔드 교체 가능
4. **재사용성**: MCP 서버를 다른 프로젝트에서도 사용 