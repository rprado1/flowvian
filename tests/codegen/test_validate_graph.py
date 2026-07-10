from __future__ import annotations

from app.codegen.generator import validate_graph


def test_validate_graph_no_nodes() -> None:
    errors = validate_graph([], [], require_trigger=False)
    assert any("Workflow has no nodes" in err for err in errors)


def test_validate_graph_rejects_multiple_triggers() -> None:
    nodes = [
        {"id": "n1", "type": "scheduler", "label": "S1", "config": {"interval": 1, "unit": "seconds"}},
        {"id": "n2", "type": "webhook", "label": "W1", "config": {"method": "POST", "path": "/hook"}},
    ]
    errors = validate_graph(nodes, [], require_trigger=False)
    assert any("Only one trigger node is allowed" in err for err in errors)


def test_validate_graph_requires_trigger_when_enabled() -> None:
    nodes = [{"id": "n1", "type": "wait", "label": "W", "config": {"seconds": 1}}]
    errors = validate_graph(nodes, [], require_trigger=True)
    assert any("must have exactly one trigger" in err for err in errors)


def test_validate_graph_non_merge_cannot_have_multiple_incoming() -> None:
    nodes = [
        {"id": "a", "type": "wait", "label": "A", "config": {"seconds": 1}},
        {"id": "b", "type": "wait", "label": "B", "config": {"seconds": 1}},
        {"id": "c", "type": "wait", "label": "C", "config": {"seconds": 1}},
    ]
    edges = [
        {"source_node_id": "a", "source_output_name": "output_1", "target_node_id": "c", "target_input_name": "input_1"},
        {"source_node_id": "b", "source_output_name": "output_1", "target_node_id": "c", "target_input_name": "input_1"},
    ]
    errors = validate_graph(nodes, edges, require_trigger=False)
    assert any("Only 'merge' nodes can have multiple incoming edges" in err for err in errors)


def test_validate_graph_merge_requires_matching_incoming_edges() -> None:
    nodes = [
        {"id": "a", "type": "wait", "label": "A", "config": {"seconds": 1}},
        {"id": "b", "type": "wait", "label": "B", "config": {"seconds": 1}},
        {"id": "m", "type": "merge", "label": "Merge", "config": {"strategy": "append", "branch_count": 3, "output_var": "merged_items"}},
    ]
    edges = [
        {"source_node_id": "a", "source_output_name": "output_1", "target_node_id": "m", "target_input_name": "input_1"},
        {"source_node_id": "b", "source_output_name": "output_1", "target_node_id": "m", "target_input_name": "input_2"},
    ]
    errors = validate_graph(nodes, edges, require_trigger=False)
    assert any("merge requires 3 incoming edges" in err for err in errors)


def test_validate_graph_detects_cycle() -> None:
    nodes = [
        {"id": "a", "type": "wait", "label": "A", "config": {"seconds": 1}},
        {"id": "b", "type": "wait", "label": "B", "config": {"seconds": 1}},
    ]
    edges = [
        {"source_node_id": "a", "source_output_name": "output_1", "target_node_id": "b", "target_input_name": "input_1"},
        {"source_node_id": "b", "source_output_name": "output_1", "target_node_id": "a", "target_input_name": "input_1"},
    ]
    errors = validate_graph(nodes, edges, require_trigger=False)
    assert any("contains a cycle" in err for err in errors)
