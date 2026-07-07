"""
Integrate Agent (结果整合).

角色定义: gather every upstream agent's output into one FinalPlan and render the Markdown package.
输入格式: ctx.outputs["parse"|"design"|"content"|"data"|"architecture"]
输出格式: FinalPlan + ctx.outputs["integrate"]
约束条件: pure aggregation + render; no re-generation of content.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.export.markdown import render_markdown


class FinalPlan(BaseModel):
    session_id: str
    markdown: str
    functions: list[dict]
    mock_data: dict[str, list[dict]]
    architecture: str
    demo_script: dict


REQUIRED_UPSTREAM = ("parse", "design", "content", "data", "architecture")


class IntegrateAgent:
    name = "integrate"

    async def run(self, ctx: AgentContext) -> FinalPlan:
        missing = [k for k in REQUIRED_UPSTREAM if k not in ctx.outputs]
        if missing:
            raise AgentError(self.name, f"missing upstream outputs: {','.join(missing)}")

        md = render_markdown(
            parse=ctx.outputs["parse"],
            design=ctx.outputs["design"],
            content=ctx.outputs["content"],
            data=ctx.outputs["data"],
            architecture=ctx.outputs["architecture"],
        )
        final = FinalPlan(
            session_id=ctx.session_id,
            markdown=md,
            functions=ctx.outputs["design"]["features"],
            mock_data=ctx.outputs["data"]["tables"],
            architecture=ctx.outputs["architecture"]["mermaid"],
            demo_script=ctx.outputs["content"],
        )
        ctx.outputs[self.name] = final.model_dump()
        return final
