"""
🤖 LLM CLIENT (공용 모듈)
========================
역할: 다양한 LLM 백엔드를 통합 관리하는 공용 클라이언트

📖 지원 백엔드:
- OpenAI API (gpt-3.5-turbo, gpt-4 등)
- HuggingFace Transformers
- GGUF 로컬 모델
- 기타 확장 가능한 백엔드

🎯 사용처:
- Agent Chain: 계획 수립 및 재계획
- Planner: LLM 기반 분석 계획
- SQL Agent: 자연어 → SQL 변환
- Server API: 채팅 완료 요청 처리

🔧 설정:
- 환경변수: LLM_BACKEND, OPENAI_MODEL, OPENAI_API_KEY
- 동적 백엔드 선택 및 설정
"""

import os
import sys
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    """LLM 클라이언트 베이스 클래스"""
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """채팅 완료 요청"""
        pass

class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트"""
    
    def __init__(self):
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        except ImportError:
            raise ImportError("OpenAI 패키지가 설치되지 않았습니다: pip install openai")
    
    def chat(self, messages: List[Dict[str, str]], model: str = None, **kwargs) -> str:
        if model is None:
            model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', 1000),
                temperature=kwargs.get('temperature', 0.1)
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API 호출 오류: {e}")

class HuggingFaceClient(BaseLLMClient):
    """HuggingFace Transformers 클라이언트"""
    
    def __init__(self):
        try:
            from transformers import pipeline
            model_name = os.environ.get("HF_MODEL", "microsoft/DialoGPT-medium")
            self.pipeline = pipeline("text-generation", model=model_name)
        except ImportError:
            raise ImportError("Transformers 패키지가 설치되지 않았습니다: pip install transformers")
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # 메시지를 단일 텍스트로 변환
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        prompt += "\nassistant:"
        
        try:
            result = self.pipeline(prompt, max_length=kwargs.get('max_tokens', 500))
            return result[0]['generated_text'].split("assistant:")[-1].strip()
        except Exception as e:
            raise Exception(f"HuggingFace 모델 호출 오류: {e}")

class GGUFClient(BaseLLMClient):
    """GGUF 로컬 모델 클라이언트"""
    
    def __init__(self):
        try:
            from llama_cpp import Llama
            model_path = os.environ.get("GGUF_MODEL_PATH", "./models/model.gguf")
            self.llm = Llama(model_path=model_path, n_ctx=2048)
        except ImportError:
            raise ImportError("llama-cpp-python 패키지가 설치되지 않았습니다")
        except Exception as e:
            raise Exception(f"GGUF 모델 로드 오류: {e}")
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # 메시지를 ChatML 형식으로 변환
        prompt = ""
        for msg in messages:
            prompt += f"<|{msg['role']}|>\n{msg['content']}\n"
        prompt += "<|assistant|>\n"
        
        try:
            result = self.llm(prompt, max_tokens=kwargs.get('max_tokens', 500))
            return result['choices'][0]['text'].strip()
        except Exception as e:
            raise Exception(f"GGUF 모델 호출 오류: {e}")

# =============================================================================
# 🎯 공용 LLM 클라이언트 팩토리
# =============================================================================

def get_llm_client(backend: str = None) -> BaseLLMClient:
    """
    LLM 클라이언트 팩토리 함수
    
    Parameters:
    - backend: LLM 백엔드 선택 (openai, huggingface, gguf)
    
    Returns:
    - 선택된 LLM 클라이언트 인스턴스
    """
    if backend is None:
        backend = os.environ.get("LLM_BACKEND", "openai")
    
    backend = backend.lower()
    
    if backend == "openai":
        return OpenAIClient()
    elif backend == "huggingface" or backend == "hf":
        return HuggingFaceClient()
    elif backend == "gguf":
        return GGUFClient()
    else:
        raise ValueError(f"지원하지 않는 LLM 백엔드: {backend}")

# =============================================================================
# 🔧 LLM 클라이언트 유틸리티 함수들
# =============================================================================

def create_chat_messages(system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
    """채팅 메시지 포맷 생성"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """LLM 응답에서 JSON 추출"""
    import json
    import re
    
    # JSON 블록 찾기
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 직접 JSON 찾기
    start_idx = response.find('{')
    end_idx = response.rfind('}') + 1
    if start_idx != -1 and end_idx > start_idx:
        try:
            return json.loads(response[start_idx:end_idx])
        except json.JSONDecodeError:
            pass
    
    return None

def validate_llm_setup() -> Dict[str, Any]:
    """LLM 설정 검증"""
    backend = os.environ.get("LLM_BACKEND", "openai")
    status = {"backend": backend, "ready": False, "error": None}
    
    try:
        client = get_llm_client(backend)
        # 간단한 테스트 메시지
        test_response = client.chat([
            {"role": "user", "content": "Hello"}
        ], max_tokens=10)
        status["ready"] = True
        status["test_response"] = test_response[:50]
    except Exception as e:
        status["error"] = str(e)
    
    return status

# =============================================================================
# 🎛️ 환경 설정 헬퍼
# =============================================================================

def get_llm_config() -> Dict[str, Any]:
    """현재 LLM 설정 정보 반환"""
    return {
        "backend": os.environ.get("LLM_BACKEND", "openai"),
        "model": os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
        "api_key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "hf_model": os.environ.get("HF_MODEL", "microsoft/DialoGPT-medium"),
        "gguf_model_path": os.environ.get("GGUF_MODEL_PATH", "./models/model.gguf")
    }

def print_llm_status():
    """LLM 상태 출력 (디버깅용)"""
    config = get_llm_config()
    print("🤖 LLM Client 상태:")
    print(f"  Backend: {config['backend']}")
    print(f"  Model: {config['model']}")
    print(f"  API Key: {'✅ 설정됨' if config['api_key_set'] else '❌ 미설정'}")
    
    validation = validate_llm_setup()
    print(f"  Ready: {'✅' if validation['ready'] else '❌'}")
    if validation['error']:
        print(f"  Error: {validation['error']}")

if __name__ == "__main__":
    print_llm_status() 