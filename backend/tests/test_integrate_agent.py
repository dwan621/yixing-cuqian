from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.content_agent import ContentAgent
from app.agents.data_agent import DataAgent
from app.agents.architecture_agent import ArchitectureAgent
from app.agents.integrate_agent import IntegrateAgent, FinalPlan


async def _full_ctx():
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链管理", scale="500 人", demo_minutes=15
        ),
        outputs={},
    )
    for agent in [ParseAgent(), DesignAgent(), ContentAgent(), DataAgent(), ArchitectureAgent()]:
        await agent.run(ctx)
    return ctx


async def test_integrate_produces_final_plan():
    ctx = await _full_ctx()
    final = await IntegrateAgent().run(ctx)
    assert isinstance(final, FinalPlan)
    assert final.session_id == "s1"


async def test_integrate_markdown_contains_key_sections():
    ctx = await _full_ctx()
    final = await IntegrateAgent().run(ctx)
    md = final.markdown
    # Required sections per spec §3.3
    assert "# 售前方案" in md
    assert "## 客户需求概览" in md
    assert "## 功能演示清单" in md  # F3-3
    assert "## 系统架构" in md
    assert "## 演示话术" in md
    assert "## 模拟数据" in md  # F3-4
    assert "```mermaid" in md
    assert "flowchart TD" in md


async def test_integrate_markdown_lists_every_selected_feature():
    ctx = await _full_ctx()
    final = await IntegrateAgent().run(ctx)
    for f in ctx.outputs["design"]["features"]:
        assert f["title"] in final.markdown


async def test_integrate_writes_outputs():
    ctx = await _full_ctx()
    await IntegrateAgent().run(ctx)
    assert "integrate" in ctx.outputs
