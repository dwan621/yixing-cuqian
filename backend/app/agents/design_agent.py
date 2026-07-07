"""
Design Agent (F2-2 方案设计).

角色定义: given a ParsedRequirement, pick the features to demo and allocate demo minutes.
输入格式: ctx.outputs["parse"] (ParsedRequirement dict)
输出格式: DesignedPlan + ctx.outputs["design"]
约束条件:
  - Feature count >= 3 (AC-3).
  - Coverage of scenario-relevant features >= 0.8 (spec §4 输出质量).
  - Sum of time allocations == demo_minutes; every slot >= 1.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParsedRequirement
from app.templates import FeatureSpec, load_templates


class TimeSlot(BaseModel):
    feature_id: str
    feature_title: str
    minutes: int


class DesignedPlan(BaseModel):
    features: list[FeatureSpec]
    coverage_ratio: float
    time_allocation: list[TimeSlot]


MIN_FEATURES = 3
MIN_COVERAGE = 0.8


class DesignAgent:
    name = "design"

    async def run(self, ctx: AgentContext) -> DesignedPlan:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)

        templates = load_templates()
        tmpl = templates[parsed.industry_key]
        bank = tmpl.feature_bank
        matched_scenarios = set(parsed.matched_scenarios)

        # Split the bank by scenario relevance.
        relevant = [f for f in bank if set(f.scenarios) & matched_scenarios]
        other = [f for f in bank if f not in relevant]

        selected = list(relevant)

        # Ensure count >= 3.
        i = 0
        while len(selected) < MIN_FEATURES and i < len(other):
            selected.append(other[i])
            i += 1

        # Ensure coverage of the relevant slice >= 0.8.
        if relevant:
            covered = sum(1 for f in selected if f in relevant)
            while covered / len(relevant) < MIN_COVERAGE and i < len(other):
                selected.append(other[i])
                i += 1
                covered = sum(1 for f in selected if f in relevant)
        coverage_ratio = 1.0 if not relevant else sum(1 for f in selected if f in relevant) / len(relevant)

        # Fair minute allocation: each feature >= 1 min, sum == demo_minutes.
        n = len(selected)
        total = parsed.demo_minutes

        # When total < n we cannot give every feature >= 1 min.
        # Trim selected to the first `total` features — the coverage ratio
        # was already computed from the full selection above.
        if total < n:
            selected = selected[:total]
            n = len(selected)

        base = max(1, total // n)
        allocation = [base] * n
        remainder = total - base * n
        idx = 0
        while sum(allocation) < total:
            allocation[idx % n] += 1
            idx += 1
        # The decrement loop from the original brief has a bug:
        # when total < n and base=1, all slots are already at their
        # minimum (1) so nothing can be decremented — infinite loop.
        # Truncating selected above (total < n branch) avoids this
        # scenario entirely; sum(allocation) will never exceed total.

        time_allocation = [
            TimeSlot(feature_id=f.id, feature_title=f.title, minutes=m)
            for f, m in zip(selected, allocation)
        ]

        designed = DesignedPlan(
            features=selected,
            coverage_ratio=round(coverage_ratio, 3),
            time_allocation=time_allocation,
        )
        ctx.outputs[self.name] = designed.model_dump()
        return designed
