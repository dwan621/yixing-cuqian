"""
Architecture Agent.

角色定义: describe how the target system slots into the customer's environment; emit Mermaid.
输入格式: ctx.outputs["parse"]
输出格式: ArchitectureDoc + ctx.outputs["architecture"]
约束条件: Mermaid must be a valid flowchart TD; no external calls.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParsedRequirement
from app.templates import load_templates


class ArchitectureDoc(BaseModel):
    description: str
    mermaid: str


class ArchitectureAgent:
    name = "architecture"

    async def run(self, ctx: AgentContext) -> ArchitectureDoc:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)
        tmpl = load_templates()[parsed.industry_key]

        description = (
            f"针对 {parsed.industry_display} 行业「{parsed.scenario}」场景，"
            f"我们的系统按下列链路与客户环境对接：{tmpl.architecture_snippet.strip()}"
        )
        # Build a simple Mermaid flowchart from the architecture snippet's arrows.
        nodes = [seg.strip() for seg in tmpl.architecture_snippet.replace("\n", "").split("→") if seg.strip()]
        lines = ["flowchart TD"]
        for i, node in enumerate(nodes):
            lines.append(f'    N{i}["{node}"]')
            if i > 0:
                lines.append(f"    N{i-1} --> N{i}")
        mermaid = "\n".join(lines)

        doc = ArchitectureDoc(description=description, mermaid=mermaid)
        ctx.outputs[self.name] = doc.model_dump()
        return doc
