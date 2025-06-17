#!/usr/bin/env python3
"""
MCP Client Implementation
=========================
표준 MCP 프로토콜 클라이언트 구현
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

# MCP Python SDK import
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool, Resource, Prompt
except ImportError:
    print("MCP SDK not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool, Resource, Prompt

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """MCP 서버 설정"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    transport: str = "stdio"  # stdio or sse
    url: Optional[str] = None  # for SSE transport

@dataclass
class MCPServerConnection:
    """MCP 서버 연결 정보"""
    config: MCPServerConfig
    session: Optional[ClientSession] = None
    tools: List[Tool] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    prompts: List[Prompt] = field(default_factory=list)
    connected: bool = False
    last_error: Optional[str] = None

class MCPClient:
    """
    MCP 클라이언트
    
    여러 MCP 서버와 동시 연결을 관리하고
    도구, 리소스, 프롬프트를 통합 제공
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConnection] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def add_server(self, config: MCPServerConfig) -> bool:
        """
        MCP 서버 추가 및 연결
        
        Args:
            config: 서버 설정
            
        Returns:
            연결 성공 여부
        """
        if config.name in self.servers:
            self.logger.warning(f"Server {config.name} already exists")
            return False
            
        connection = MCPServerConnection(config=config)
        self.servers[config.name] = connection
        
        try:
            if config.transport == "stdio":
                await self._connect_stdio(connection)
            elif config.transport == "sse":
                await self._connect_sse(connection)
            else:
                raise ValueError(f"Unknown transport: {config.transport}")
                
            connection.connected = True
            self.logger.info(f"Successfully connected to {config.name}")
            return True
            
        except Exception as e:
            connection.last_error = str(e)
            self.logger.error(f"Failed to connect to {config.name}: {e}")
            return False
    
    async def _connect_stdio(self, connection: MCPServerConnection):
        """stdio 프로토콜로 서버 연결"""
        config = connection.config
        
        # 서버 파라미터 생성
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env
        )
        
        try:
            # stdio 클라이언트 생성 (context manager 사용하지 않음)
            read, write = await stdio_client(server_params).__aenter__()
            
            # 세션 생성
            session = ClientSession(read, write)
            await session.__aenter__()
            
            connection.session = session
            connection._read = read
            connection._write = write
            
            # 초기화
            await session.initialize()
            self.logger.info(f"Initialized session with {config.name}")
            
            # 도구 목록 조회
            tools_response = await session.list_tools()
            connection.tools = tools_response.tools
            self.logger.info(f"Found {len(connection.tools)} tools in {config.name}")
            
            # 리소스 목록 조회
            resources_response = await session.list_resources()
            connection.resources = resources_response.resources
            self.logger.info(f"Found {len(connection.resources)} resources in {config.name}")
            
            # 프롬프트 목록 조회
            prompts_response = await session.list_prompts()
            connection.prompts = prompts_response.prompts
            self.logger.info(f"Found {len(connection.prompts)} prompts in {config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect stdio: {e}")
            raise
    
    async def _connect_sse(self, connection: MCPServerConnection):
        """SSE 프로토콜로 서버 연결 (미구현)"""
        # TODO: SSE 구현
        raise NotImplementedError("SSE transport not yet implemented")
    
    async def _keep_session_alive(self, connection: MCPServerConnection):
        """세션 유지를 위한 더미 태스크"""
        # 실제로는 이벤트 루프에서 관리되어야 함
        pass
    
    async def remove_server(self, name: str) -> bool:
        """
        MCP 서버 연결 해제 및 제거
        
        Args:
            name: 서버 이름
            
        Returns:
            제거 성공 여부
        """
        if name not in self.servers:
            self.logger.warning(f"Server {name} not found")
            return False
            
        connection = self.servers[name]
        
        try:
            if connection.session:
                # 세션 종료
                await connection.session.__aexit__(None, None, None)
                
            # stdio 클라이언트 종료
            if hasattr(connection, '_read') and hasattr(connection, '_write'):
                stdio_ctx = stdio_client(None)
                stdio_ctx._read = connection._read
                stdio_ctx._write = connection._write
                await stdio_ctx.__aexit__(None, None, None)
                
            del self.servers[name]
            self.logger.info(f"Successfully removed {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove {name}: {e}")
            # 에러가 발생해도 제거는 수행
            if name in self.servers:
                del self.servers[name]
            return False
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """연결된 서버 목록 조회"""
        return [
            {
                "name": name,
                "transport": conn.config.transport,
                "connected": conn.connected,
                "tools": len(conn.tools),
                "resources": len(conn.resources),
                "prompts": len(conn.prompts),
                "last_error": conn.last_error
            }
            for name, conn in self.servers.items()
        ]
    
    def list_all_tools(self) -> List[Dict[str, Any]]:
        """모든 서버의 도구 목록 통합 조회"""
        tools = []
        for server_name, conn in self.servers.items():
            if conn.connected:
                for tool in conn.tools:
                    tools.append({
                        "server": server_name,
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })
        return tools
    
    def list_all_resources(self) -> List[Dict[str, Any]]:
        """모든 서버의 리소스 목록 통합 조회"""
        resources = []
        for server_name, conn in self.servers.items():
            if conn.connected:
                for resource in conn.resources:
                    resources.append({
                        "server": server_name,
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mime_type": resource.mimeType
                    })
        return resources
    
    def list_all_prompts(self) -> List[Dict[str, Any]]:
        """모든 서버의 프롬프트 목록 통합 조회"""
        prompts = []
        for server_name, conn in self.servers.items():
            if conn.connected:
                for prompt in conn.prompts:
                    prompts.append({
                        "server": server_name,
                        "name": prompt.name,
                        "description": prompt.description,
                        "arguments": prompt.arguments
                    })
        return prompts
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        도구 실행
        
        Args:
            server_name: 서버 이름
            tool_name: 도구 이름
            arguments: 도구 인자
            
        Returns:
            실행 결과
        """
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
            
        connection = self.servers[server_name]
        if not connection.connected:
            raise RuntimeError(f"Server {server_name} not connected")
            
        if not connection.session:
            raise RuntimeError(f"No session for {server_name}")
            
        try:
            # 도구 호출
            result = await connection.session.call_tool(tool_name, arguments)
            
            return {
                "success": True,
                "content": result.content,
                "is_error": result.isError
            }
            
        except Exception as e:
            self.logger.error(f"Tool call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_resource(
        self,
        server_name: str,
        uri: str
    ) -> Dict[str, Any]:
        """
        리소스 읽기
        
        Args:
            server_name: 서버 이름
            uri: 리소스 URI
            
        Returns:
            리소스 내용
        """
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
            
        connection = self.servers[server_name]
        if not connection.connected:
            raise RuntimeError(f"Server {server_name} not connected")
            
        if not connection.session:
            raise RuntimeError(f"No session for {server_name}")
            
        try:
            # 리소스 읽기
            result = await connection.session.read_resource(uri)
            
            return {
                "success": True,
                "contents": result.contents,
                "uri": uri
            }
            
        except Exception as e:
            self.logger.error(f"Resource read failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_prompt(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        프롬프트 가져오기
        
        Args:
            server_name: 서버 이름
            prompt_name: 프롬프트 이름
            arguments: 프롬프트 인자
            
        Returns:
            프롬프트 내용
        """
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
            
        connection = self.servers[server_name]
        if not connection.connected:
            raise RuntimeError(f"Server {server_name} not connected")
            
        if not connection.session:
            raise RuntimeError(f"No session for {server_name}")
            
        try:
            # 프롬프트 가져오기
            result = await connection.session.get_prompt(
                prompt_name,
                arguments=arguments or {}
            )
            
            return {
                "success": True,
                "messages": result.messages,
                "description": result.description
            }
            
        except Exception as e:
            self.logger.error(f"Prompt get failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_all(self):
        """모든 서버 연결 종료"""
        for name in list(self.servers.keys()):
            await self.remove_server(name) 