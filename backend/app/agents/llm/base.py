"""LLMAgentBase — shared prompt→API→JSON→pydantic pipeline."""
from __future__ import annotations
import json
import re
from pydantic import BaseModel
from app.agents.base import AgentError
from app.agents.llm import client

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)
_UNQUOTED_KEY_RE = re.compile(r'(?<=\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:')
_SINGLE_QUOTE_KEY_RE = re.compile(r"'([a-zA-Z_][a-zA-Z0-9_]*)':")


def _fix_llm_json(raw: str) -> str:
    """Fix common LLM JSON formatting errors: unquoted keys, single quotes, trailing commas."""
    result = raw.strip()

    # 1. Quote bare property names: {key: "val"} → {"key": "val"}
    result = _UNQUOTED_KEY_RE.sub(r'"\1":', result)

    # 2. Single-quoted keys: {'key': 'val'} → {"key": "val"}
    result = _SINGLE_QUOTE_KEY_RE.sub(r'"\1":', result)

    # 3. Single-quoted values: {'val'} → {"val"} (careful: don't touch contractions like it's)
    result = result.replace("':' ", '":" ').replace("':'", '":"')  # single-quoted dict values → double
    result = result.replace(", '", ', "').replace(": '", ': "')  # remaining single quotes → double

    # 4. Remove trailing commas before } or ]
    result = re.sub(r',\s*(\}|\])', r'\1', result)

    # 5. Remove leading/trailing non-JSON text
    first_brace = result.find('{')
    last_brace = result.rfind('}')
    if first_brace >= 0 and last_brace > first_brace:
        result = result[first_brace:last_brace + 1]

    return result


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

        # Attempt 3: fix common LLM JSON errors and retry
        fixed = _fix_llm_json(raw)
        try:
            data = json.loads(fixed)
            return output_model.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            errors.append(f"after fix: {e}")

        raise AgentError(
            self.name,
            f"LLM response not parseable as {output_model.__name__}: {'; '.join(errors[-3:])}",
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
