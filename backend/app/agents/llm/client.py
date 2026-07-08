"""Volcengine Ark API client — OpenAI-compatible wrapper."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (backend/) or parent directory
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from openai import AsyncOpenAI

ARK_BASE = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/plan/v3")
ARK_KEY = os.getenv("ARK_API_KEY", "")
ARK_MODEL = os.getenv("ARK_MODEL", "ark-code-latest")
TIMEOUT = 60
MAX_RETRIES = 2

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not ARK_KEY:
            raise RuntimeError("ARK_API_KEY environment variable is not set")
        _client = AsyncOpenAI(
            api_key=ARK_KEY,
            base_url=ARK_BASE,
            timeout=TIMEOUT,
            max_retries=MAX_RETRIES,
        )
    return _client


async def complete(prompt: str, *, temperature: float = 0.3, max_tokens: int = 4096) -> str:
    client = get_client()
    resp = await client.chat.completions.create(
        model=ARK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if not resp.choices:
        raise RuntimeError("LLM returned empty choices")
    content = resp.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM returned null content")
    return content
