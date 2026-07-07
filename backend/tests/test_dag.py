from app.agents.registry import AGENT_REGISTRY
from app.orchestrator.dag import DAG, AgentNode, topological_layers


def test_registry_contains_expected_agents():
    assert set(AGENT_REGISTRY.keys()) == {"parse", "design", "content", "data", "architecture", "integrate"}


def test_dag_has_six_nodes():
    assert len(DAG) == 6


def test_dag_dependencies_form_the_fan_out():
    by_name = {n.name: n for n in DAG}
    assert by_name["parse"].depends_on == ()
    assert by_name["design"].depends_on == ("parse",)
    assert set(by_name["content"].depends_on) == {"design"}
    assert set(by_name["data"].depends_on) == {"design"}
    assert set(by_name["architecture"].depends_on) == {"parse"}
    assert set(by_name["integrate"].depends_on) == {"content", "data", "architecture"}


def test_topological_layers_group_fan_out_together():
    layers = topological_layers(DAG)
    layer_names = [{n.name for n in layer} for layer in layers]
    assert layer_names[0] == {"parse"}
    assert layer_names[1] == {"design", "architecture"} or layer_names[1] == {"design"}
    # architecture depends only on parse, so it can be in layer 1; content/data must land after design.
    idx = {name: i for i, layer in enumerate(layers) for name in {n.name for n in layer}}
    assert idx["parse"] < idx["design"]
    assert idx["design"] < idx["content"]
    assert idx["design"] < idx["data"]
    assert idx["parse"] < idx["architecture"]
    assert idx["integrate"] == max(idx.values())


def test_topological_layers_cycle_raises():
    import pytest
    cycle = (AgentNode("a", ("b",)), AgentNode("b", ("a",)))
    with pytest.raises(ValueError):
        topological_layers(cycle)
