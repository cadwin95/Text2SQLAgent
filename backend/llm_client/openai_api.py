# openai_api.py
# -------------
# OpenAI API 기반 LLM 백엔드 구현 파일
# - base.py의 LLMClient 추상화를 상속하여 구현
# - OpenAI API 호출, generate/chat 메서드 제공
# - MCP 서버/Agent에서 외부 LLM(OpenAI 등) API 연동 시 사용
# - API 키/엔드포인트/요금제 관리 등 포함
# - 자세한 설계/구현 규칙은 .cursor/rules/rl-text2sql-public-api.md 참고

from .base import LLMClient
from openai import OpenAI

class OpenAIClient(LLMClient):
    """
    OpenAI API 기반 LLMClient 구현체
    - chat: OpenAI chat/completions 엔드포인트 호출
    - generate: 단일 프롬프트를 chat 포맷으로 감싸서 호출
    """
    def __init__(self, api_key=None, base_url=None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages, **kwargs):
        response = self.client.chat.completions.create(
            model=kwargs.get("model", "gpt-3.5-turbo"),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 256),
            temperature=kwargs.get("temperature", 0.1),
        )
        return response.choices[0].message.content

    def generate(self, prompt, **kwargs):
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)
