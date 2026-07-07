"""
Orchestration engine.

- Groups the DAG into topological layers; runs each layer's nodes concurrently.
- Emits AgentEvent through an optional callback for progress streaming.
- On failure, records the failure but lets sibling nodes in the same layer finish
  before raising PipelineFailure (spec §4 容错性, AC-6).
"""
from __future__ import annotations
import time
from typing import Awaitable, Callable
import anyio

from app.agents.base import Agent, AgentContext, AgentError
from app.agents.registry import AGENT_REGISTRY
from app.orchestrator.dag import AgentNode, DAG, topological_layers
from app.orchestrator.events import AgentEvent

EventCallback = Callable[[AgentEvent], Awaitable[None]]


class PipelineFailure(Exception):
    def __init__(self, failures: list[AgentEvent]) -> None:
        msg = "; ".join(f"{ev.agent}: {ev.error}" for ev in failures)
        super().__init__(msg)
        self.failures = failures


async def _run_one(
    node: AgentNode,
    agent: Agent,
    ctx: AgentContext,
    on_event: EventCallback | None,
    failures: list[AgentEvent],
) -> None:
    if on_event:
        await on_event(AgentEvent(agent=node.name, status="running"))
    started = time.monotonic()
    try:
        await agent.run(ctx)
        elapsed = int((time.monotonic() - started) * 1000)
        if on_event:
            await on_event(AgentEvent(agent=node.name, status="done", elapsed_ms=elapsed))
    except AgentError as e:
        elapsed = int((time.monotonic() - started) * 1000)
        ev = AgentEvent(agent=node.name, status="failed", elapsed_ms=elapsed, error=e.reason)
        failures.append(ev)
        if on_event:
            await on_event(ev)
    except Exception as e:  # unexpected — surface with the Agent's name (AC-6)
        elapsed = int((time.monotonic() - started) * 1000)
        ev = AgentEvent(agent=node.name, status="failed", elapsed_ms=elapsed, error=f"unexpected: {e}")
        failures.append(ev)
        if on_event:
            await on_event(ev)


async def run_pipeline(
    ctx: AgentContext,
    on_event: EventCallback | None = None,
    registry: dict[str, Agent] | None = None,
    dag: tuple[AgentNode, ...] | None = None,
) -> dict:
    reg = registry or AGENT_REGISTRY
    active_dag = dag or DAG

    # Validate all DAG node names exist in the registry.
    missing = [n.name for n in active_dag if n.name not in reg]
    if missing:
        raise ValueError(f"DAG nodes not found in registry: {missing}")

    layers = topological_layers(active_dag)
    failures: list[AgentEvent] = []
    failed_names: set[str] = set()

    for layer in layers:
        runnable = [n for n in layer if not (set(n.depends_on) & failed_names)]
        # Skipped nodes (upstream failed) are also reported for transparency.
        for n in layer:
            if n not in runnable and on_event:
                await on_event(AgentEvent(
                    agent=n.name,
                    status="failed",
                    error=f"skipped: upstream {sorted(set(n.depends_on) & failed_names)} failed",
                ))
                failed_names.add(n.name)

        async with anyio.create_task_group() as tg:
            for node in runnable:
                agent = reg[node.name]
                tg.start_soon(_run_one, node, agent, ctx, on_event, failures)

        for ev in failures:
            failed_names.add(ev.agent)

    if failures:
        raise PipelineFailure(failures)

    return ctx.outputs["integrate"]
