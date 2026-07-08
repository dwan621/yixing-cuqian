"""Agent registry with LLM_MODE toggle. Defaults to template agents.

LLM_MODE values:
  template (default) — existing YAML/template-based agents, no API key needed
  llm               — Volcengine Ark LLM-backed agents, requires ARK_API_KEY
  hybrid            — LLM first, template fallback on AgentError
"""
from __future__ import annotations
import os
from app.agents.base import Agent


def _template_registry() -> dict[str, Agent]:
    from app.agents.parse_agent import ParseAgent
    from app.agents.design_agent import DesignAgent
    from app.agents.content_agent import ContentAgent
    from app.agents.data_agent import DataAgent
    from app.agents.architecture_agent import ArchitectureAgent
    from app.agents.integrate_agent import IntegrateAgent
    return {
        "parse": ParseAgent(),
        "design": DesignAgent(),
        "content": ContentAgent(),
        "data": DataAgent(),
        "architecture": ArchitectureAgent(),
        "integrate": IntegrateAgent(),
    }


def _llm_registry() -> dict[str, Agent]:
    from app.agents.integrate_agent import IntegrateAgent  # template — pure assembly
    from app.agents.llm.parse_agent import LLMParseAgent
    from app.agents.llm.design_agent import LLMDesignAgent
    from app.agents.llm.content_agent import LLMContentAgent
    from app.agents.llm.data_agent import LLMDataAgent
    from app.agents.llm.architecture_agent import LLMArchitectureAgent
    return {
        "parse": LLMParseAgent(),
        "design": LLMDesignAgent(),
        "content": LLMContentAgent(),
        "data": LLMDataAgent(),
        "architecture": LLMArchitectureAgent(),
        "integrate": IntegrateAgent(),  # always template — pure Markdown assembly
    }


def _hybrid_registry() -> dict[str, Agent]:
    from app.agents.parse_agent import ParseAgent
    from app.agents.design_agent import DesignAgent
    from app.agents.content_agent import ContentAgent
    from app.agents.data_agent import DataAgent
    from app.agents.architecture_agent import ArchitectureAgent
    from app.agents.integrate_agent import IntegrateAgent
    from app.agents.llm.parse_agent import LLMParseAgent
    from app.agents.llm.design_agent import LLMDesignAgent
    from app.agents.llm.content_agent import LLMContentAgent
    from app.agents.llm.data_agent import LLMDataAgent
    from app.agents.llm.architecture_agent import LLMArchitectureAgent
    from app.agents.llm.integrate_agent import LLMIntegrateAgent
    from app.agents.llm.base import HybridAgent
    return {
        "parse": HybridAgent(LLMParseAgent(), ParseAgent()),
        "design": HybridAgent(LLMDesignAgent(), DesignAgent()),
        "content": HybridAgent(LLMContentAgent(), ContentAgent()),
        "data": HybridAgent(LLMDataAgent(), DataAgent()),
        "architecture": HybridAgent(LLMArchitectureAgent(), ArchitectureAgent()),
        "integrate": IntegrateAgent(),  # always template — pure assembly
    }


def _build_registry() -> dict[str, Agent]:
    mode = os.getenv("LLM_MODE", "template").lower()
    if mode == "llm":
        return _llm_registry()
    elif mode == "hybrid":
        return _hybrid_registry()
    elif mode == "template":
        return _template_registry()
    else:
        raise ValueError(f"Invalid LLM_MODE='{mode}'. Use 'template', 'llm', or 'hybrid'.")


AGENT_REGISTRY: dict[str, Agent] = _build_registry()
