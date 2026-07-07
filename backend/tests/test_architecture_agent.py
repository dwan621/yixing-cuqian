from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.architecture_agent import ArchitectureAgent, ArchitectureDoc


async def _ctx(industry="制造业"):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry=industry, scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    return ctx


async def test_architecture_agent_returns_document():
    ctx = await _ctx()
    doc = await ArchitectureAgent().run(ctx)
    assert isinstance(doc, ArchitectureDoc)
    assert doc.description
    assert doc.mermaid.startswith("flowchart TD")


async def test_architecture_agent_description_mentions_industry():
    ctx = await _ctx("金融")
    doc = await ArchitectureAgent().run(ctx)
    assert "金融" in doc.description


async def test_architecture_agent_writes_outputs():
    ctx = await _ctx()
    await ArchitectureAgent().run(ctx)
    assert "architecture" in ctx.outputs
