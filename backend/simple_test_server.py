# simple_test_server.py
# =====================
# 간단한 테스트용 FastAPI 서버
# - 모델 로딩 없이 고정된 응답 제공
# - 프론트엔드 연동 테스트용

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import time
import random

# FastAPI 앱 설정
app = FastAPI(
    title="Text2SQL Test Server",
    description="프론트엔드 연동 테스트용 간단한 API 서버",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI 호환 API를 위한 Pydantic 모델 정의
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.1

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-test"
    object: str = "chat.completion"
    model: str = "text2sql-test"
    choices: List[ChatCompletionResponseChoice]

# 샘플 SQL 쿼리들
SAMPLE_QUERIES = [
    "SELECT * FROM population WHERE country = '한국' ORDER BY year DESC LIMIT 10;",
    "SELECT year, gdp_growth_rate FROM economic_indicators WHERE country = '한국' AND year >= 2019;",
    "SELECT region, AVG(house_price) as avg_price FROM real_estate WHERE city = '서울' GROUP BY region;",
    "SELECT * FROM employment_stats WHERE year = 2023 AND country = '한국';",
    "SELECT industry, COUNT(*) as company_count FROM companies WHERE location LIKE '%서울%' GROUP BY industry;",
]

@app.get("/")
def read_root():
    return {
        "message": "Text2SQL Test Server가 실행 중입니다.",
        "status": "healthy",
        "endpoints": ["/v1/chat/completions", "/health"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    try:
        # 사용자 메시지 추출
        user_message = ""
        for message in request.messages:
            if message.role == "user":
                user_message = message.content
                break
        
        # 간단한 키워드 기반 SQL 생성
        sql_query = generate_sample_sql(user_message)
        
        # 응답 생성
        response = ChatCompletionResponse(
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=sql_query
                    )
                )
            ]
        )
        
        # 약간의 지연 시뮬레이션 (실제 AI 처리 시간 모방)
        await asyncio.sleep(0.5)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

def generate_sample_sql(user_input: str) -> str:
    """사용자 입력에 따라 샘플 SQL 쿼리 생성"""
    user_input_lower = user_input.lower()
    
    if any(keyword in user_input_lower for keyword in ["인구", "population"]):
        return "SELECT year, population FROM population_stats WHERE country = '한국' ORDER BY year DESC LIMIT 5;"
    
    elif any(keyword in user_input_lower for keyword in ["gdp", "경제", "성장률"]):
        return "SELECT year, gdp_growth_rate, gdp_nominal FROM economic_indicators WHERE country = '한국' AND year >= 2020 ORDER BY year;"
    
    elif any(keyword in user_input_lower for keyword in ["부동산", "집값", "house", "real estate"]):
        return "SELECT region, AVG(price) as avg_price, COUNT(*) as transaction_count FROM real_estate_transactions WHERE city = '서울' AND year = 2023 GROUP BY region ORDER BY avg_price DESC;"
    
    elif any(keyword in user_input_lower for keyword in ["고용", "취업", "employment"]):
        return "SELECT age_group, employment_rate, unemployment_rate FROM employment_stats WHERE country = '한국' AND year = 2023 ORDER BY age_group;"
    
    elif any(keyword in user_input_lower for keyword in ["기업", "회사", "company"]):
        return "SELECT industry, COUNT(*) as company_count, AVG(employees) as avg_employees FROM companies WHERE country = '한국' GROUP BY industry ORDER BY company_count DESC LIMIT 10;"
    
    else:
        # 기본 쿼리 (랜덤 선택)
        return random.choice(SAMPLE_QUERIES)

# 비동기 처리를 위한 import
import asyncio

if __name__ == "__main__":
    print("🚀 Text2SQL Test Server 시작 중...")
    print("📍 URL: http://localhost:8000")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔗 프론트엔드 연동: http://localhost:3000")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    ) 