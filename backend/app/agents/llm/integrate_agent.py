"""LLM-backed Integrate Agent (结果整合)."""
from __future__ import annotations
from app.agents.base import AgentContext, AgentError
from app.agents.integrate_agent import FinalPlan
from app.agents.llm.base import LLMAgentBase
from app.agents.llm.prompts import integrate_prompt

REQUIRED_UPSTREAM = ("parse", "design", "content", "data", "architecture")


class LLMIntegrateAgent(LLMAgentBase):
    name = "integrate"

    async def run(self, ctx: AgentContext) -> FinalPlan:
        missing = [k for k in REQUIRED_UPSTREAM if k not in ctx.outputs]
        if missing:
            raise AgentError(self.name, f"missing upstream outputs: {','.join(missing)}")

        prompt = integrate_prompt(
            parse=ctx.outputs["parse"],
            design=ctx.outputs["design"],
            content=ctx.outputs["content"],
            data=ctx.outputs["data"],
            architecture=ctx.outputs["architecture"],
        )

        final = await self._llm(prompt, FinalPlan)
        ctx.outputs[self.name] = final.model_dump()
        return final
