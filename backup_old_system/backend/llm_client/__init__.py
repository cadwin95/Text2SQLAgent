# __init__.py
# ===========
# LLMClient 팩토리 모듈 - 다양한 LLM 백엔드 통합 관리
# - OpenAI API, HuggingFace Transformers, GGUF(llama.cpp) 등 지원
# - get_llm_client() 팩토리 함수를 통해 백엔드별 클라이언트 인스턴스 생성
# - AgentChain, Text2SQL Agent 등에서 LLM 추상화 계층으로 활용
# - 백엔드별 설정, 모델 파라미터, API 키 등을 통합 관리
# - 확장 가능한 아키텍처로 새로운 LLM 엔진 추가 용이
# - 자세한 설계/구현 규칙은 .cursor/rules/rl-text2sql-public-api.md 참고

# LLMClient 팩토리 함수

def get_llm_client(backend, **kwargs):
    if backend == "openai":
        from .openai_api import OpenAIClient
        return OpenAIClient(**kwargs)
    elif backend == "huggingface":
        from .huggingface import HuggingFaceClient
        return HuggingFaceClient(**kwargs)
    elif backend == "gguf":
        from .gguf import GGUFClient
        return GGUFClient(**kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend}")
