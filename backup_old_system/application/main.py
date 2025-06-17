#!/usr/bin/env python3
"""
MCP-based Text2SQL Agent Application
====================================
MCP 서버들과 LLM을 통합하는 메인 애플리케이션
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Install with: pip install python-dotenv")

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import 모듈들
from mcp_client.client import MCPClient, MCPServerConfig
from application.llm.manager import LLMManager
from application.agent.orchestrator import AgentOrchestrator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPApplication:
    """
    MCP 기반 애플리케이션
    
    - 여러 MCP 서버 관리
    - LLM 통합
    - Agent 실행
    """
    
    def __init__(self, config_path: str = "mcp_servers/config/servers.json"):
        self.config_path = config_path
        self.mcp_client = MCPClient()
        self.llm_manager = LLMManager()
        self.agent = None
        self.servers_config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """서버 설정 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"servers": []}
    
    async def initialize(self):
        """애플리케이션 초기화"""
        logger.info("Initializing MCP Application...")
        
        # 1. LLM 초기화
        llm_backend = os.getenv("LLM_BACKEND", "openai")
        self.llm_manager.initialize(llm_backend)
        logger.info(f"LLM initialized: {llm_backend}")
        
        # 2. MCP 서버들 연결
        await self._connect_servers()
        
        # 3. Agent 초기화
        self.agent = AgentOrchestrator(
            mcp_client=self.mcp_client,
            llm_manager=self.llm_manager
        )
        logger.info("Agent orchestrator initialized")
        
    async def _connect_servers(self):
        """설정된 MCP 서버들 연결"""
        servers = self.servers_config.get("servers", [])
        
        for server_config in servers:
            if not server_config.get("enabled", False):
                continue
                
            try:
                # 환경 변수 치환
                env = server_config.get("env", {})
                for key, value in env.items():
                    if value.startswith("${") and value.endswith("}"):
                        env_var = value[2:-1]
                        env[key] = os.getenv(env_var, "")
                
                # 서버 설정 생성
                config = MCPServerConfig(
                    name=server_config["name"],
                    command=server_config["command"],
                    args=server_config.get("args", []),
                    env=env,
                    transport=server_config.get("transport", "stdio")
                )
                
                # 서버 연결
                logger.info(f"Connecting to {config.name}...")
                success = await self.mcp_client.add_server(config)
                
                if success:
                    logger.info(f"✅ Connected to {config.name}")
                else:
                    logger.warning(f"❌ Failed to connect to {config.name}")
                    
            except Exception as e:
                logger.error(f"Error connecting to server: {e}")
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        사용자 쿼리 처리
        
        Args:
            query: 사용자 질의
            
        Returns:
            처리 결과
        """
        if not self.agent:
            return {
                "success": False,
                "error": "Application not initialized"
            }
            
        try:
            # Agent 실행
            result = await self.agent.process(query)
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """애플리케이션 상태 조회"""
        return {
            "llm": {
                "backend": self.llm_manager.backend_type if self.llm_manager else None,
                "ready": self.llm_manager.is_initialized if self.llm_manager else False
            },
            "mcp_servers": self.mcp_client.list_servers() if self.mcp_client else [],
            "tools": len(self.mcp_client.list_all_tools()) if self.mcp_client else 0,
            "resources": len(self.mcp_client.list_all_resources()) if self.mcp_client else 0,
            "prompts": len(self.mcp_client.list_all_prompts()) if self.mcp_client else 0,
            "agent_ready": self.agent is not None
        }
    
    async def shutdown(self):
        """애플리케이션 종료"""
        logger.info("Shutting down MCP Application...")
        
        if self.mcp_client:
            await self.mcp_client.close_all()
            
        logger.info("Shutdown complete")

async def main():
    """메인 함수"""
    # 애플리케이션 생성
    app = MCPApplication()
    
    try:
        # 초기화
        await app.initialize()
        
        # 상태 출력
        status = app.get_status()
        print("\n=== Application Status ===")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 예제 쿼리 실행
        print("\n=== Example Query ===")
        query = "2023년 서울시 인구 통계를 보여주세요"
        print(f"Query: {query}")
        
        result = await app.process_query(query)
        print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
    finally:
        # 종료
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 