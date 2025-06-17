"""
LLM Manager
===========
다양한 LLM 백엔드를 통합 관리하는 매니저
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
import json

logger = logging.getLogger(__name__)

class LLMBackend(ABC):
    """LLM 백엔드 추상 클래스"""
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """채팅 완성"""
        pass
    
    @abstractmethod
    def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        """스트리밍 채팅"""
        pass

class OpenAIBackend(LLMBackend):
    """OpenAI API 백엔드"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = model
            logger.info(f"OpenAI backend initialized with model: {model}")
        except ImportError:
            raise ImportError("openai package not installed")
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """OpenAI 채팅 완성"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise
    
    def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        """OpenAI 스트리밍 채팅"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
            raise

class HuggingFaceBackend(LLMBackend):
    """HuggingFace 백엔드 (구현 예정)"""
    
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        # TODO: 실제 구현
        logger.warning("HuggingFace backend not fully implemented")
        self.model_name = model_name
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """HuggingFace 채팅 완성"""
        # TODO: transformers 라이브러리 사용
        return "HuggingFace response (not implemented)"
    
    def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        """HuggingFace 스트리밍 채팅"""
        yield "HuggingFace streaming (not implemented)"

class GGUFBackend(LLMBackend):
    """GGUF/llama.cpp 백엔드 (구현 예정)"""
    
    def __init__(self, model_path: str):
        # TODO: 실제 구현
        logger.warning("GGUF backend not fully implemented")
        self.model_path = model_path
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """GGUF 채팅 완성"""
        # TODO: llama-cpp-python 사용
        return "GGUF response (not implemented)"
    
    def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        """GGUF 스트리밍 채팅"""
        yield "GGUF streaming (not implemented)"

class LLMManager:
    """
    LLM 매니저
    
    다양한 LLM 백엔드를 통합 관리
    """
    
    def __init__(self):
        self.backend: Optional[LLMBackend] = None
        self.backend_name: Optional[str] = None
        
    def initialize(self, backend: str = "openai", **kwargs):
        """
        LLM 백엔드 초기화
        
        Args:
            backend: 백엔드 종류 (openai, huggingface, gguf)
            **kwargs: 백엔드별 설정
        """
        try:
            if backend == "openai":
                api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
                model = kwargs.get("model") or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                self.backend = OpenAIBackend(api_key=api_key, model=model)
                
            elif backend == "huggingface":
                model_name = kwargs.get("model_name", "microsoft/DialoGPT-medium")
                self.backend = HuggingFaceBackend(model_name=model_name)
                
            elif backend == "gguf":
                model_path = kwargs.get("model_path", "./models/llama-2-7b.gguf")
                self.backend = GGUFBackend(model_path=model_path)
                
            else:
                raise ValueError(f"Unknown backend: {backend}")
                
            self.backend_name = backend
            logger.info(f"LLM Manager initialized with {backend} backend")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM backend: {e}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        채팅 완성
        
        Args:
            messages: 메시지 리스트
            **kwargs: 추가 파라미터
            
        Returns:
            응답 텍스트
        """
        if not self.backend:
            raise RuntimeError("LLM backend not initialized")
            
        return self.backend.chat(messages, **kwargs)
    
    def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        """
        스트리밍 채팅
        
        Args:
            messages: 메시지 리스트
            **kwargs: 추가 파라미터
            
        Yields:
            응답 청크
        """
        if not self.backend:
            raise RuntimeError("LLM backend not initialized")
            
        yield from self.backend.stream_chat(messages, **kwargs)
    
    def create_mcp_aware_prompt(
        self,
        query: str,
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        MCP 도구를 인식하는 프롬프트 생성
        
        Args:
            query: 사용자 질의
            available_tools: 사용 가능한 도구 목록
            context: 추가 컨텍스트
            
        Returns:
            메시지 리스트
        """
        # 시스템 프롬프트
        system_prompt = """You are an AI assistant with access to various tools through the Model Context Protocol (MCP).

Available tools:
"""
        for tool in available_tools:
            system_prompt += f"\n- {tool['name']}: {tool.get('description', 'No description')}"
            
        system_prompt += """

When you need to use a tool, respond with:
TOOL_CALL: {
    "server": "server_name",
    "tool": "tool_name",
    "arguments": {...}
}

After getting tool results, continue with your analysis."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        # 컨텍스트 추가
        if context:
            context_msg = f"\nContext: {json.dumps(context, ensure_ascii=False)}"
            messages[0]["content"] += context_msg
            
        return messages
    
    @property
    def is_initialized(self) -> bool:
        """초기화 여부"""
        return self.backend is not None
    
    @property
    def backend_type(self) -> str:
        """현재 백엔드 타입"""
        return self.backend_name or "none" 