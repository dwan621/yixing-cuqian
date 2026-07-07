import pytest
from app.schemas import RequirementInput
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParseAgent, ParsedRequirement


def _ctx(**overrides):
    req = RequirementInput(
        industry=overrides.get("industry", "制造业"),
        scenario=overrides.get("scenario", "供应链管理"),
        scale=overrides.get("scale", "500 人以上"),
        demo_minutes=overrides.get("demo_minutes", 15),
        background=overrides.get("background"),
    )
    return AgentContext(session_id="s1", requirement=req, outputs={})


async def test_parse_agent_maps_industry_by_alias():
    ctx = _ctx()
    parsed = await ParseAgent().run(ctx)
    assert isinstance(parsed, ParsedRequirement)
    assert parsed.industry_key == "manufacturing"
    assert parsed.industry_display == "制造业"


async def test_parse_agent_writes_outputs_under_its_name():
    ctx = _ctx()
    await ParseAgent().run(ctx)
    assert "parse" in ctx.outputs
    assert ctx.outputs["parse"]["industry_key"] == "manufacturing"


async def test_parse_agent_extracts_matched_scenarios_from_background():
    ctx = _ctx(scenario="供应链管理", background="也想看看质量管理和 OEE")
    parsed = await ParseAgent().run(ctx)
    assert "供应链管理" in parsed.matched_scenarios
    assert "质量管理" in parsed.matched_scenarios


async def test_parse_agent_defaults_matched_scenarios_to_input_scenario():
    ctx = _ctx(scenario="供应链管理", background=None)
    parsed = await ParseAgent().run(ctx)
    assert parsed.matched_scenarios == ["供应链管理"]


async def test_parse_agent_raises_on_unknown_industry():
    ctx = _ctx(industry="外星科技")
    with pytest.raises(AgentError) as excinfo:
        await ParseAgent().run(ctx)
    assert excinfo.value.agent_name == "parse"
    assert "外星科技" in excinfo.value.reason
