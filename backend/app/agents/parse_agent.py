"""
Parse Agent (F2-1 需求解析).

角色定义: extract structured requirement (industry, scenario, scale, matched scenarios) from raw form input.
输入格式: AgentContext.requirement: RequirementInput
输出格式: ParsedRequirement + ctx.outputs["parse"] = same as dict
约束条件: no LLM call, template-lookup only; raise AgentError on unknown industry.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.templates import load_templates, resolve_industry


class ParsedRequirement(BaseModel):
    industry_key: str
    industry_display: str
    scenario: str
    scale: str
    demo_minutes: int
    background: str | None
    matched_scenarios: list[str]


class ParseAgent:
    name = "parse"

    async def run(self, ctx: AgentContext) -> ParsedRequirement:
        req = ctx.requirement
        templates = load_templates()
        tmpl = resolve_industry(req.industry, templates)
        if tmpl is None:
            raise AgentError(self.name, f"unknown industry: {req.industry}")

        # Collect scenarios that appear either in scenario input or in the free-text background.
        haystack = " ".join([req.scenario, req.background or ""]).lower()
        matched = [s for s in tmpl.default_scenarios if s.lower() in haystack]
        if req.scenario not in matched:
            matched.insert(0, req.scenario)

        parsed = ParsedRequirement(
            industry_key=tmpl.name.lower(),
            industry_display=req.industry,
            scenario=req.scenario,
            scale=req.scale,
            demo_minutes=req.demo_minutes,
            background=req.background,
            matched_scenarios=matched,
        )
        ctx.outputs[self.name] = parsed.model_dump()
        return parsed
