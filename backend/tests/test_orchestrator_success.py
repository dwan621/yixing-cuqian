from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.orchestrator.engine import run_pipeline
from app.orchestrator.events import AgentEvent


def _ctx():
    return AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )


async def test_pipeline_returns_integrate_output():
    ctx = _ctx()
    result = await run_pipeline(ctx)
    assert "markdown" in result
    assert "# 售前方案" in result["markdown"]


async def test_pipeline_emits_running_and_done_for_each_agent():
    events: list[AgentEvent] = []

    async def sink(ev: AgentEvent) -> None:
        events.append(ev)

    ctx = _ctx()
    await run_pipeline(ctx, on_event=sink)
    agent_names = {"parse", "design", "content", "data", "architecture", "integrate"}
    running = {ev.agent for ev in events if ev.status == "running"}
    done = {ev.agent for ev in events if ev.status == "done"}
    assert running == agent_names
    assert done == agent_names


async def test_pipeline_records_elapsed_ms_non_negative():
    events: list[AgentEvent] = []

    async def sink(ev: AgentEvent) -> None:
        events.append(ev)

    ctx = _ctx()
    await run_pipeline(ctx, on_event=sink)
    for ev in events:
        if ev.status == "done":
            assert ev.elapsed_ms >= 0
