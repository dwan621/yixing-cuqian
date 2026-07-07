import pytest
from app.schemas import RequirementInput
from app.agents.base import Agent, AgentContext, AgentError, AgentResult


def _ctx():
    return AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )


class _StubAgent:
    name = "stub"

    async def run(self, ctx: AgentContext):
        ctx.outputs[self.name] = {"echo": ctx.requirement.industry}
        return ctx.outputs[self.name]


async def test_stub_agent_conforms_to_protocol():
    a: Agent = _StubAgent()  # type: ignore[assignment]
    ctx = _ctx()
    out = await a.run(ctx)
    assert out == {"echo": "制造业"}
    assert ctx.outputs["stub"] == {"echo": "制造业"}


def test_agent_error_stringifies_agent_and_reason():
    err = AgentError(agent_name="parse", reason="missing industry")
    assert str(err) == "parse: missing industry"
    assert err.agent_name == "parse"
    assert err.reason == "missing industry"


def test_agent_result_success_shape():
    r = AgentResult(agent_name="parse", ok=True, value={"a": 1}, error=None, elapsed_ms=42)
    assert r.ok
    assert r.value == {"a": 1}
    assert r.error is None


def test_agent_result_failure_shape():
    r = AgentResult(agent_name="parse", ok=False, value=None, error="boom", elapsed_ms=5)
    assert not r.ok
    assert r.error == "boom"
