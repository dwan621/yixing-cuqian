"""LLM-backed Content Agent (F2-3)."""
from __future__ import annotations
from app.agents.base import AgentContext, AgentError
from app.agents.content_agent import DemoScript
from app.agents.llm.base import LLMAgentBase
from app.agents.llm.prompts import content_prompt


class LLMContentAgent(LLMAgentBase):
    name = "content"

    async def run(self, ctx: AgentContext) -> DemoScript:
        parse_out = ctx.outputs.get("parse")
        design_out = ctx.outputs.get("design")
        if parse_out is None or design_out is None:
            raise AgentError(self.name, "upstream parse/design output missing")

        prompt = content_prompt(parsed=parse_out, design=design_out)

        script = await self._llm(prompt, DemoScript, max_tokens=16384)
        ctx.outputs[self.name] = script.model_dump()
        return script
