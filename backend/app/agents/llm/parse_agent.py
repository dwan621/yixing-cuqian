"""LLM-backed Parse Agent (F2-1)."""
from __future__ import annotations
from app.agents.base import AgentContext
from app.agents.parse_agent import ParsedRequirement
from app.templates import load_templates
from app.agents.llm.base import LLMAgentBase
from app.agents.llm.prompts import parse_prompt


class LLMParseAgent(LLMAgentBase):
    name = "parse"

    async def run(self, ctx: AgentContext) -> ParsedRequirement:
        req = ctx.requirement
        templates = load_templates()

        industry_ref = []
        for key, tmpl in templates.items():
            aliases_str = "、".join(tmpl.aliases) if tmpl.aliases else "无"
            scenarios_str = "、".join(tmpl.default_scenarios)
            industry_ref.append(
                f"  - name: {key}, 显示名: {tmpl.name}, 别名: [{aliases_str}], 默认场景: [{scenarios_str}]"
            )
        known = "\n".join(industry_ref)

        prompt = parse_prompt(
            industry=req.industry,
            scenario=req.scenario,
            scale=req.scale,
            demo_minutes=req.demo_minutes,
            background=req.background,
            known_industries=known,
        )

        parsed = await self._llm(prompt, ParsedRequirement)
        
        # Validate: raise AgentError if industry_key not in known templates
        if parsed.industry_key not in templates:
            from app.agents.base import AgentError
            raise AgentError(self.name, f"unknown industry: {req.industry} (LLM returned {parsed.industry_key})")
        
        ctx.outputs[self.name] = parsed.model_dump()
        return parsed
