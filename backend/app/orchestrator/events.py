from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

AgentStatus = Literal["running", "done", "failed"]


@dataclass
class AgentEvent:
    agent: str
    status: AgentStatus
    elapsed_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return {"agent": self.agent, "status": self.status, "elapsed_ms": self.elapsed_ms, "error": self.error}
