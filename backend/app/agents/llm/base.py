"""LLMAgentBase — shared prompt→API→JSON→pydantic pipeline."""
from __future__ import annotations
import json
import re
from pydantic import BaseModel
from app.agents.base import AgentError
from app.agents.llm import client

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


class LLMAgentBase:
    name: str

    async def _llm(self, prompt: str, output_model: type[BaseModel], max_tokens: int = 8192) -> BaseModel:
        raw = await client.complete(prompt, max_tokens=max_tokens)
        return self._parse_or_raise(raw, output_model)

    def _parse_or_raise(self, raw: str, output_model: type[BaseModel]) -> BaseModel:
        errors: list[str] = []

        # Attempt 1: direct JSON parse
        try:
            data = json.loads(raw)
            return output_model.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            errors.append(str(e))

        # Attempt 2: extract from ```json ... ``` fence
        match = _FENCE_RE.search(raw)
        if match:
            try:
                data = json.loads(match.group(1))
                return output_model.model_validate(data)
            except (json.JSONDecodeError, Exception) as e:
                errors.append(str(e))

        raise AgentError(
            self.name,
            f"LLM response not parseable as {output_model.__name__}: {'; '.join(errors[-2:])}",
        )


class HybridAgent:
    """Tries LLM agent first; falls back to template agent on AgentError."""

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback
        self.name = primary.name

    async def run(self, ctx):
        try:
            return await self._primary.run(ctx)
        except AgentError:
            return await self._fallback.run(ctx)
