"""LLM-backed Data Agent (F2-4)."""
from __future__ import annotations
import json
from app.agents.base import AgentContext, AgentError
from app.agents.data_agent import MockDataPack
from app.agents.parse_agent import ParsedRequirement
from app.templates import load_templates
from app.agents.llm.base import LLMAgentBase
from app.agents.llm.prompts import data_prompt


class LLMDataAgent(LLMAgentBase):
    name = "data"

    async def run(self, ctx: AgentContext) -> MockDataPack:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)

        tmpl = load_templates()[parsed.industry_key]
        schema_ref = json.dumps(tmpl.mock_data_schema, ensure_ascii=False, indent=2)

        prompt = data_prompt(parsed=parse_out, schema_ref=schema_ref)

        pack = await self._llm(prompt, MockDataPack, max_tokens=16384)
        ctx.outputs[self.name] = pack.model_dump()
        return pack
