"""LLM-backed Design Agent (F2-2)."""
from __future__ import annotations
import json
from app.agents.base import AgentContext, AgentError
from app.agents.design_agent import DesignedPlan
from app.agents.parse_agent import ParsedRequirement
from app.templates import load_templates
from app.agents.llm.base import LLMAgentBase
from app.agents.llm.prompts import design_prompt


class LLMDesignAgent(LLMAgentBase):
    name = "design"

    async def run(self, ctx: AgentContext) -> DesignedPlan:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)

        tmpl = load_templates()[parsed.industry_key]
        feature_bank_json = json.dumps(
            [f.model_dump() for f in tmpl.feature_bank], ensure_ascii=False, indent=2
        )

        prompt = design_prompt(parsed=parse_out, feature_bank_json=feature_bank_json)

        designed = await self._llm(prompt, DesignedPlan)
        ctx.outputs[self.name] = designed.model_dump()
        return designed
