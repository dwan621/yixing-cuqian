"""Orchestrator failure path tests — AC-6 (fault isolation).

Proves: a failing agent does not kill sibling agents on independent
branches, the engine surfaces the failing agent's name + reason, and
an early-stage failure blocks everything downstream.
"""
import pytest
from app.schemas import RequirementInput
from app.agents.base import AgentContext, AgentError
from app.agents.registry import AGENT_REGISTRY
from app.orchestrator.engine import run_pipeline, PipelineFailure


class _FailingContentAgent:
    """A content agent that always fails — injected in place of the real one."""

    name = "content"

    async def run(self, ctx: AgentContext):
        raise AgentError("content", "LLM timeout, please retry")


def _ctx():
    return AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )


@pytest.mark.asyncio
async def test_pipeline_raises_pipeline_failure_when_content_fails():
    """A failing content agent must produce a PipelineFailure naming it."""
    registry = dict(AGENT_REGISTRY)
    registry["content"] = _FailingContentAgent()
    with pytest.raises(PipelineFailure) as excinfo:
        await run_pipeline(_ctx(), registry=registry)
    failures = excinfo.value.failures
    assert any(f.agent == "content" for f in failures), "must report content failure"


@pytest.mark.asyncio
async def test_sibling_agents_data_and_architecture_still_succeed():
    """Data and Architecture don't depend on Content; they must complete (spec §4, AC-6)."""
    registry = dict(AGENT_REGISTRY)
    registry["content"] = _FailingContentAgent()
    ctx = _ctx()
    try:
        await run_pipeline(ctx, registry=registry)
    except PipelineFailure:
        pass

    assert "data" in ctx.outputs, "data agent independent of content — must complete"
    assert "architecture" in ctx.outputs, (
        "architecture agent independent of content — must complete"
    )
    assert "integrate" not in ctx.outputs, (
        "integrate depends on content — must be skipped"
    )


@pytest.mark.asyncio
async def test_failing_parse_blocks_everything():
    """If the very first agent fails, no downstream agent should run."""
    registry = dict(AGENT_REGISTRY)

    class _FailingParseAgent:
        name = "parse"

        async def run(self, ctx: AgentContext):
            raise AgentError("parse", "unknown industry")

    registry["parse"] = _FailingParseAgent()
    ctx = _ctx()
    try:
        await run_pipeline(ctx, registry=registry)
    except PipelineFailure:
        pass

    assert "design" not in ctx.outputs
    assert "content" not in ctx.outputs
