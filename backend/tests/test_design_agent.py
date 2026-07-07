import pytest
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent, DesignedPlan


async def _run(industry="制造业", scenario="供应链管理", background=None, minutes=15):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry=industry, scenario=scenario, scale="500 人", demo_minutes=minutes,
            background=background,
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    plan = await DesignAgent().run(ctx)
    return ctx, plan


async def test_design_agent_produces_at_least_three_features():
    _, plan = await _run()
    assert len(plan.features) >= 3  # AC-3


async def test_design_agent_features_relevant_to_scenario():
    _, plan = await _run(scenario="供应链管理")
    for f in plan.features:
        # Every returned feature must at least touch a matched scenario.
        assert f.scenarios, f"feature {f.id} has no scenarios"


async def test_design_agent_coverage_at_least_80_percent():
    _, plan = await _run()
    assert plan.coverage_ratio >= 0.8  # spec §4 输出质量


async def test_design_agent_time_allocation_sums_to_demo_minutes():
    _, plan = await _run(minutes=15)
    assert sum(slot.minutes for slot in plan.time_allocation) == 15


async def test_design_agent_time_allocation_matches_feature_count():
    _, plan = await _run(minutes=15)
    assert len(plan.time_allocation) == len(plan.features)


async def test_design_agent_writes_outputs():
    ctx, _ = await _run()
    assert "design" in ctx.outputs
    assert isinstance(ctx.outputs["design"]["features"], list)


async def test_design_agent_handles_short_demo_minutes_without_zero_slots():
    _, plan = await _run(minutes=3)
    # 3 features minimum, each must get >= 1 minute; total == 3.
    assert all(s.minutes >= 1 for s in plan.time_allocation)
    assert sum(s.minutes for s in plan.time_allocation) == 3
