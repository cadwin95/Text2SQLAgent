"""Minimal natural language to SQL conversion using OpenAI API."""

from __future__ import annotations

import os
from typing import Optional

try:
    import openai
except Exception:  # pragma: no cover - openai may not be installed
    openai = None

DEFAULT_SYSTEM_PROMPT = (
    "You are an assistant that converts natural language questions into SQL "
    "queries. Only return the SQL query as your answer."
)

async def nl2sql(question: str, *, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    """Convert a natural language question into a SQL query using OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or openai is None:
        # Fallback when OpenAI is not configured
        return "SELECT 1"

    openai.api_key = api_key
    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    # Assume the assistant returns the SQL in the first message
    sql = response.choices[0].message.content.strip()
    return sql
