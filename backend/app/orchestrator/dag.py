"""
DAG definition. Data-only; editing this file does not touch the runner (engine.py).
Adding a new Agent means: implement it, register it, add one AgentNode line here.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentNode:
    name: str
    depends_on: tuple[str, ...] = ()


DAG: tuple[AgentNode, ...] = (
    AgentNode("parse"),
    AgentNode("design", depends_on=("parse",)),
    AgentNode("content", depends_on=("design",)),
    AgentNode("data", depends_on=("design",)),
    AgentNode("architecture", depends_on=("parse",)),
    AgentNode("integrate", depends_on=("content", "data", "architecture")),
)


def topological_layers(dag: tuple[AgentNode, ...]) -> list[list[AgentNode]]:
    by_name = {n.name: n for n in dag}
    remaining = {n.name: set(n.depends_on) for n in dag}
    layers: list[list[AgentNode]] = []
    while remaining:
        ready = [name for name, deps in remaining.items() if not deps]
        if not ready:
            raise ValueError(f"cycle detected in DAG; remaining={remaining}")
        layers.append([by_name[n] for n in ready])
        for name in ready:
            del remaining[name]
        for deps in remaining.values():
            deps.difference_update(ready)
    return layers
