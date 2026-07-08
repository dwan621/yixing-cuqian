"""LLM-backed Architecture Agent."""
from __future__ import annotations
from app.agents.base import AgentContext, AgentError
from app.agents.architecture_agent import ArchitectureDoc
from app.agents.llm.base import LLMAgentBase
from app.agents.llm.prompts import architecture_prompt


class LLMArchitectureAgent(LLMAgentBase):
    name = "architecture"

    async def run(self, ctx: AgentContext) -> ArchitectureDoc:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")

        from app.agents.parse_agent import ParsedRequirement
        from app.templates import load_templates

        parsed = ParsedRequirement.model_validate(parse_out)
        tmpl = load_templates()[parsed.industry_key]
        snippet = tmpl.architecture_snippet

        prompt = architecture_prompt(parsed=parse_out, snippet=snippet)

        doc = await self._llm(prompt, ArchitectureDoc)
        ctx.outputs[self.name] = doc.model_dump()
        return doc
