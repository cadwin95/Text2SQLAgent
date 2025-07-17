"""
Main FastAPI Application with MindsDB-inspired Multi-Database Support
다중 데이터베이스 지원 메인 애플리케이션
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys

# 데이터베이스 API 임포트
from .api.database_api import router as database_router
from .api.agent_api import router as agent_router
from .database.connection_manager import get_connection_manager


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작
    logger.info("Starting MindsDB-inspired Multi-Database System")
    
    try:
        # 연결 매니저 초기화
        connection_manager = get_connection_manager()
        logger.info("Connection Manager initialized successfully")
        
        # 라우터 등록 확인 
        logger.info("Database router registered with prefix: /api/database")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise e
    
    yield
    
    # 종료
    logger.info("Shutting down application...")
    
    # 모든 데이터베이스 연결 해제
    try:
        await connection_manager.disconnect_all()
        logger.info("All database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing connections: {e}")


# FastAPI 앱 생성
app = FastAPI(
    title="Text2SQL Agent - Multi-Database System",
    description="MindsDB-inspired multi-database connection and query system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 API 라우터 등록
app.include_router(database_router)
app.include_router(agent_router)


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    # 등록된 라우터 정보 수집
    registered_routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            registered_routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else ["GET"]
            })
    
    return {
        "message": "Text2SQL Agent - Multi-Database System",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "Multi-database connections",
            "SQL query execution", 
            "Schema exploration",
            "Connection management",
            "MindsDB-inspired architecture"
        ],
        "registered_routes_count": len(registered_routes),
        "sample_database_endpoints": [
            "/api/database/connections",
            "/api/database/connections/test",
            "/api/database/query",
            "/api/database/schema"
        ]
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        connection_manager = get_connection_manager()
        stats = connection_manager.get_connection_stats()
        
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "connections": stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/api/info")
async def api_info():
    """API 정보 엔드포인트"""
    from .database.handlers.handler_factory import get_supported_databases
    
    try:
        supported_dbs = get_supported_databases()
        
        return {
            "api_version": "1.0.0",
            "supported_databases": supported_dbs,
            "endpoints": {
                "connections": "/api/database/connections",
                "query": "/api/database/query",
                "schema": "/api/database/schema",
                "health": "/api/database/health"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get API info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API info")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 