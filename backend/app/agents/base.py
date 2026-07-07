from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict
from app.schemas import RequirementInput


class AgentContext(BaseModel):
    """Passed to every Agent. `outputs` is mutable; other fields are frozen."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    requirement: RequirementInput
    outputs: dict[str, Any]


@runtime_checkable
class Agent(Protocol):
    name: str

    async def run(self, ctx: AgentContext) -> Any: ...


class AgentError(Exception):
    """Raised by an Agent to signal a controlled failure with the Agent's name attached.

    The orchestrator catches this, records the failure, and continues siblings on
    independent branches (spec §4 容错性, AC-6).
    """

    def __init__(self, agent_name: str, reason: str) -> None:
        super().__init__(f"{agent_name}: {reason}")
        self.agent_name = agent_name
        self.reason = reason


@dataclass
class AgentResult:
    agent_name: str
    ok: bool
    value: Any
    error: str | None
    elapsed_ms: int
