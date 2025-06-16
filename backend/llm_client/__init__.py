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
