"""
Content Agent (F2-3 内容生成).

角色定义: turn a DesignedPlan into demo copy — 功能介绍 / 操作流程 / 价值说明 / 话术.
输入格式: ctx.outputs["design"] (DesignedPlan dict)
输出格式: DemoScript + ctx.outputs["content"]
约束条件: template-driven; use each feature's built-in demo_steps and talking_points; never invent numbers.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.design_agent import DesignedPlan
from app.agents.parse_agent import ParsedRequirement


class FeatureBrief(BaseModel):
    feature_id: str
    title: str
    intro: str
    flow: list[str]
    value: str
    talking_points_5min: str
    talking_points_15min: str


class DemoScript(BaseModel):
    briefs: list[FeatureBrief]
    opening: str
    closing: str


class ContentAgent:
    name = "content"

    async def run(self, ctx: AgentContext) -> DemoScript:
        parse_out = ctx.outputs.get("parse")
        design_out = ctx.outputs.get("design")
        if parse_out is None or design_out is None:
            raise AgentError(self.name, "upstream parse/design output missing")
        parsed = ParsedRequirement.model_validate(parse_out)
        designed = DesignedPlan.model_validate(design_out)

        briefs: list[FeatureBrief] = []
        for f in designed.features:
            short_tp = f.talking_points[0] if f.talking_points else f.title
            long_tp = " / ".join(f.talking_points) if f.talking_points else f.title
            briefs.append(FeatureBrief(
                feature_id=f.id,
                title=f.title,
                intro=f.description,
                flow=f.demo_steps,
                value=long_tp,
                talking_points_5min=short_tp,
                talking_points_15min=long_tp,
            ))

        opening = (
            f"针对{parsed.industry_display}行业，围绕「{parsed.scenario}」场景，"
            f"我们准备了 {len(briefs)} 个核心功能演示，覆盖客户最关心的能力。"
        )
        closing = (
            f"以上是为{parsed.industry_display}客户量身准备的方案要点，"
            f"欢迎针对任何模块深入交流。"
        )
        script = DemoScript(briefs=briefs, opening=opening, closing=closing)
        ctx.outputs[self.name] = script.model_dump()
        return script
