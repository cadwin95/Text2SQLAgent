# base.py
# -------
# LLMClient 추상화의 공통 인터페이스(ABC) 정의 파일
# - 다양한 LLM 엔진(HuggingFace, OpenAI API, 로컬 gguf 등) 지원을 위한 기반 클래스
# - 모든 LLM 백엔드는 이 클래스를 상속하여 구현
# - 주요 메서드: generate(prompt, ...), chat(messages, ...), load_model(), unload_model() 등
# - MCP 서버/Agent와 연동되는 LLM 호출의 일관성/확장성 보장
# - 자세한 설계/구현 규칙은 .cursor/rules/rl-text2sql-public-api.md 참고

from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages, **kwargs):
        """
        OpenAI API 스타일의 chat 메시지 리스트로 LLM을 호출하는 메서드
        Args:
            messages (list): [{"role": "user", "content": "..."}, ...]
            **kwargs: 모델별 추가 옵션
        Returns:
            str: LLM의 응답 텍스트
        """
        pass

    @abstractmethod
    def generate(self, prompt, **kwargs):
        """
        단일 프롬프트로 LLM을 호출하는 메서드 (옵션)
        Args:
            prompt (str): 입력 프롬프트
            **kwargs: 모델별 추가 옵션
        Returns:
            str: LLM의 응답 텍스트
        """
        pass

# ... (구현 예정)
pass
