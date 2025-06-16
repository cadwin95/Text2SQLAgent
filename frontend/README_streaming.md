# 🔄 실시간 툴 호출 표시 기능

## 개요

Text2SQL Agent에 **실시간 스트리밍** 기능이 추가되어, 사용자가 질의를 보내면 다음과 같은 과정을 UI에서 실시간으로 확인할 수 있습니다:

- 🎯 **분석 계획 수립**
- 🔧 **도구 호출 상태** (KOSIS API, DataFrame 쿼리 등)
- 📊 **데이터 처리 과정**
- 📈 **최종 결과 생성**

## 주요 특징

### 1. 실시간 진행 상황 표시
```
🚀 분석을 시작합니다...
📋 계획 수립 완료: 3개 단계
🔧 도구 호출: fetch_kosis_data (🔄 실행 중...)
✅ 도구 실행 완료: fetch_kosis_data
📊 데이터 쿼리 실행 중...
📈 최종 결과를 생성 중입니다...
```

### 2. 툴 실행 상태 시각화
- 🔄 **실행 중**: 노란색 점멸 표시
- ✅ **완료**: 초록색 완료 표시  
- ❌ **오류**: 빨간색 오류 표시

### 3. 상세한 메타데이터
- 실행 시간
- 툴 파라미터
- 데이터프레임 크기
- 오류 메시지

## 사용 방법

### 백엔드 API

#### 기존 API (일반 응답)
```http
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "text2sql",
  "messages": [{"role": "user", "content": "한국의 인구 통계를 보여주세요"}]
}
```

#### 새로운 스트리밍 API
```http
POST /v1/chat/stream
Content-Type: application/json

{
  "model": "text2sql", 
  "messages": [{"role": "user", "content": "한국의 인구 통계를 보여주세요"}]
}
```

### 프론트엔드 사용

ChatContainer에서 스트리밍 기능이 자동으로 활성화됩니다:

```typescript
// 사용자가 메시지를 보내면 자동으로 스트리밍 처리
const handleSendMessage = async (content: string) => {
  // 스트리밍 API 호출
  await sendChatMessageStream({
    message: content,
    sessionId: activeSessionId,
  }, (update) => {
    // 실시간 업데이트 처리
    switch (update.type) {
      case 'start': // 시작
      case 'step': // 단계 진행
      case 'tool_call': // 툴 호출
      case 'query': // 쿼리 실행
      case 'result': // 최종 결과
      case 'error': // 오류
      case 'done': // 완료
    }
  });
};
```

## 스트리밍 메시지 타입

### 1. start
```json
{
  "type": "start",
  "message": "분석을 시작합니다...",
  "status": "running"
}
```

### 2. step (단계 진행)
```json
{
  "type": "step", 
  "step": "planning",
  "message": "✅ 계획 수립 완료: 3개 단계",
  "status": "completed",
  "data": {
    "steps": ["KOSIS 데이터 조회", "데이터 분석", "결과 시각화"]
  }
}
```

### 3. tool_call (툴 호출)
```json
{
  "type": "tool_call",
  "tool_name": "fetch_kosis_data", 
  "message": "✅ 도구 실행 완료: fetch_kosis_data",
  "status": "completed",
  "data": {
    "df_shape": [1000, 5],
    "df_name": "fetch_kosis_data_DT_1B040A3"
  }
}
```

### 4. query (데이터 쿼리)
```json
{
  "type": "query",
  "message": "✅ 쿼리 실행 완료", 
  "status": "completed",
  "data": {
    "columns": ["지역", "인구수", "연도"],
    "rows": [["서울", 9720846, 2024]]
  }
}
```

### 5. result (최종 결과)
```json
{
  "type": "result",
  "message": "📈 분석 결과:\n\n| 지역 | 인구수 | 연도 |\n|------|--------|------|\n| 서울 | 9,720,846 | 2024 |",
  "status": "completed",
  "data": {
    "final_result": {...}
  }
}
```

### 6. error (오류)
```json
{
  "type": "error", 
  "message": "❌ KOSIS API 호출 중 오류가 발생했습니다",
  "status": "error"
}
```

### 7. done (완료)
```json
{
  "type": "done",
  "message": "분석이 완료되었습니다.",
  "status": "completed"
}
```

## 테스트 방법

### 1. 백엔드 테스트
```bash
cd backend
python test_streaming.py
```

### 2. 프론트엔드 테스트
1. 백엔드 서버 실행: `python integrated_api_server.py`
2. 프론트엔드 실행: `npm run dev`
3. http://localhost:3000 접속
4. "한국의 인구 통계를 보여주세요" 등의 질의 입력

## UI 개선 사항

### MessageBubble 컴포넌트
- 🔧 **툴 실행 상태** 섹션 추가
- 💫 **실시간 분석 중** 애니메이션 표시
- 📊 **진행 상황** 시각적 표시

### 예시 화면
```
[사용자] 한국의 인구 통계를 보여주세요

[AI 응답]
🚀 분석을 시작합니다...

📋 계획 수립
✅ 계획 수립 완료: 3개 단계
1. KOSIS에서 인구 통계 조회
2. 데이터 분석 및 요약  
3. 결과 시각화

🔧 도구 실행 상태:
● fetch_kosis_data ✅ 완료

💫 실시간 분석 중...

📈 분석 결과:
| 지역 | 인구수 | 증감률 |
|------|--------|--------|
| 서울 | 9,720,846 | -0.91% |
| 부산 | 3,349,016 | -1.64% |
```

## 기술적 세부사항

### 백엔드 (FastAPI)
- **StreamingResponse** 사용
- **Server-Sent Events (SSE)** 형식
- **비동기 생성자** 패턴

### 프론트엔드 (React/TypeScript)
- **Fetch API Streaming** 사용
- **실시간 상태 업데이트**
- **Zustand Store** 메시지 관리

### 주의사항
- 스트리밍 연결은 30초 타임아웃
- 대용량 데이터 전송 시 청크 단위 처리
- 오류 발생 시 자동 폴백 처리 