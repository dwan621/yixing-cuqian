"""Single swap point for Agent instances. Replace with LLM-backed instances per spec §5.4."""
from __future__ import annotations
from app.agents.base import Agent
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.content_agent import ContentAgent
from app.agents.data_agent import DataAgent
from app.agents.architecture_agent import ArchitectureAgent
from app.agents.integrate_agent import IntegrateAgent

AGENT_REGISTRY: dict[str, Agent] = {
    "parse": ParseAgent(),
    "design": DesignAgent(),
    "content": ContentAgent(),
    "data": DataAgent(),
    "architecture": ArchitectureAgent(),
    "integrate": IntegrateAgent(),
}
