from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.content_agent import ContentAgent, DemoScript, FeatureBrief


async def _prepped_ctx(scenario="供应链管理", minutes=15):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario=scenario, scale="500 人", demo_minutes=minutes
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    await DesignAgent().run(ctx)
    return ctx


async def test_content_agent_produces_one_brief_per_feature():
    ctx = await _prepped_ctx()
    script = await ContentAgent().run(ctx)
    assert isinstance(script, DemoScript)
    assert len(script.briefs) == len(ctx.outputs["design"]["features"])


async def test_content_agent_briefs_include_talking_points_variants():
    ctx = await _prepped_ctx()
    script = await ContentAgent().run(ctx)
    for b in script.briefs:
        assert isinstance(b, FeatureBrief)
        assert b.talking_points_5min
        assert b.talking_points_15min
        assert b.flow, "demo flow must not be empty (spec §3.3 F3-3)"


async def test_content_agent_opening_mentions_industry_and_scenario():
    ctx = await _prepped_ctx(scenario="供应链管理")
    script = await ContentAgent().run(ctx)
    assert "制造" in script.opening or "manufacturing" in script.opening.lower()
    assert "供应链" in script.opening


async def test_content_agent_writes_outputs():
    ctx = await _prepped_ctx()
    await ContentAgent().run(ctx)
    assert "content" in ctx.outputs
    assert isinstance(ctx.outputs["content"]["briefs"], list)
