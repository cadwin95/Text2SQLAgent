# api_server.py
# -------------
# ⚠️ **LEGACY FILE - DEPRECATED**
# 이 파일은 더 이상 사용되지 않습니다.
# 대신 `integrated_api_server.py`를 사용하세요.
# 
# FastAPI 등으로 구현된 백엔드 API 서버 메인 파일
# - LLM/Text2SQL/공공API 연동 엔드포인트 제공 (RESTful API)
# - 프론트엔드(채팅 UI 등) 및 외부 서비스와의 통신 담당
# - 다양한 LLM 백엔드(HuggingFace, OpenAI, gguf 등)와 연동
# - 자연어 질의→LLM→파라미터 추출→공공API→결과 반환 파이프라인 체인 자동화
# - 공식 규칙/명세(.cursor/rules/rl-text2sql-public-api.md) 기반 설계/구현
# - 확장성/유지보수성/테스트 용이성 고려

# TODO (2024.06 기준, RL 기반 Text2SQL+공공API 자동화 관점)
# - LLM 체인 연동(검색→메타→파라미터→조회) 자동화 미흡
# - RL reward/실행 결과 기반 피드백 구조 미구현
# - 각 엔드포인트별 테스트/문서화 보강 필요

"""
⚠️ DEPRECATED: 이 파일은 더 이상 사용되지 않습니다.

대신 `integrated_api_server.py`를 사용하세요:
- 더 완전한 AgentChain 통합
- 실시간 스트리밍 지원  
- DataFrame 기반 처리
- KOSIS API 연동

실행 방법:
python integrated_api_server.py

---

Hugging Face의 'Snowflake/Arctic-Text2SQL-R1-7B' 모델을 로컬에서 로드하고,
FastAPI를 사용하여 OpenAI와 호환되는 API 엔드포인트를 제공하는 서버입니다.

이 서버를 실행하면, 로컬 머신에서 Text-to-SQL 모델을 직접 구동할 수 있으며,
'llm_text2sql_agent.py'와 같은 클라이언트가 이 서버에 요청을 보내
자연어 질의를 SQL로 변환할 수 있습니다.

실행 방법:
1. `pip install -r requirements.txt`로 모든 패키지를 설치합니다.
2. 터미널에서 `python api_server.py`를 실행합니다.
3. 서버가 성공적으로 실행되면, Uvicorn이 `http://127.0.0.1:8000`에서 실행 중임을 알립니다.
"""

import torch
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Optional
import os

print("⚠️  WARNING: 이 파일(api_server.py)은 DEPRECATED입니다.")
print("🚀 대신 다음 명령어를 사용하세요:")
print("   python integrated_api_server.py")
print("")

# --- 모델 및 토크나이저 로드 ---
# MODEL_NAME = "Snowflake/Arctic-Text2SQL-R1-7B" # 더 이상 필요 없음
LOCAL_MODEL_PATH = "./model-cache"

print(f"Loading model from local path '{LOCAL_MODEL_PATH}'...")
print("Please run 'download_model.py' first if you haven't.")

# 로컬 모델 경로가 존재하는지 확인
if not os.path.exists(LOCAL_MODEL_PATH):
    print(f"Error: Local model directory not found at '{LOCAL_MODEL_PATH}'")
    print("Please run 'python download_model.py' to download the model first.")
    exit(1)

try:
    # 로컬 디렉터리에서 모델과 토크나이저를 로드
    tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        LOCAL_MODEL_PATH
    )
    model.to("cpu")
    print("Model loaded successfully from local path onto CPU.")
except Exception as e:
    print(f"Error loading model: {e}")
    print("Please ensure you have a compatible environment (GPU with CUDA recommended).")
    # 모델 로딩 실패 시 서버 실행 중단
    exit(1)


# --- FastAPI 앱 설정 ---
app = FastAPI(
    title="Local Text-to-SQL LLM Server",
    description=f"An API server for the {LOCAL_MODEL_PATH} model, compatible with OpenAI's API format."
)

# --- OpenAI 호환 API를 위한 Pydantic 모델 정의 ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str # OpenAI API 형식상 필요하지만, 여기서는 사용되지 않음
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.1

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-local"
    object: str = "chat.completion"
    model: str = LOCAL_MODEL_PATH
    choices: List[ChatCompletionResponseChoice]


# --- API 엔드포인트 정의 ---
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    # 실제 모델 추론 대신 항상 고정된 샘플 SQL 반환
    return JSONResponse({
        "choices": [
            {"message": {"content": "SELECT * FROM apartments;"}}
        ]
    })

@app.get("/")
def read_root():
    return {"message": f"Welcome to the {LOCAL_MODEL_PATH} API server. Visit /docs for API documentation."}


# --- 서버 실행 ---
if __name__ == "__main__":
    # `reload=True`는 코드 변경 시 서버를 자동으로 재시작하여 개발에 유용합니다.
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 