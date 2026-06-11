"""
Code Generator
==============
Takes a workflow graph (nodes + edges) and produces a standalone Python script
that can be compiled to an .exe with PyInstaller.

Execution order is determined via topological sort of the DAG formed by edges.
If a Scheduler node is present it wraps all subsequent nodes in a while-True loop.
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Optional
from app.nodes.base import BaseNode
from app.nodes.scheduler import SchedulerNode
from app.nodes.set_variables import SetVariablesNode
from app.nodes.get_current_date import GetCurrentDateUTCNode
from app.nodes.add_time_to_date import AddTimeToDateNode


NODE_REGISTRY: dict[str, type[BaseNode]] = {
    SchedulerNode.NODE_TYPE: SchedulerNode,
    SetVariablesNode.NODE_TYPE: SetVariablesNode,
    GetCurrentDateUTCNode.NODE_TYPE: GetCurrentDateUTCNode,
    AddTimeToDateNode.NODE_TYPE: AddTimeToDateNode,
}

SCRIPT_HEADER = '''\
# ============================================================
# Auto-generated workflow script
# DO NOT EDIT MANUALLY
# ============================================================
import sys
import os
'''


def _build_node(node_data: dict) -> BaseNode:
    node_type = node_data["type"]
    cls = NODE_REGISTRY.get(node_type)
    if cls is None:
        raise ValueError(f"Unknown node type: '{node_type}'")
    return cls(node_id=node_data["id"], config=node_data.get("config", {}))


def _topological_sort(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """
    Returns nodes sorted in execution order using Kahn's algorithm (BFS topological sort).
    Raises ValueError on cycles.
    """
    node_map = {n["id"]: n for n in nodes}
    in_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        src = edge["source_node_id"]
        tgt = edge["target_node_id"]
        adjacency[src].append(tgt)
        in_degree[tgt] += 1

    # Initialise queue with nodes that have no incoming edges
    queue: deque[str] = deque(
        node_id for node_id in node_map if in_degree[node_id] == 0
    )
    sorted_nodes: list[dict] = []

    while queue:
        node_id = queue.popleft()
        sorted_nodes.append(node_map[node_id])
        for neighbor in adjacency[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_nodes) != len(nodes):
        raise ValueError("Workflow contains a cycle — cannot generate code")

    return sorted_nodes


def validate_graph(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Validate all nodes and return a flat list of error messages."""
    errors: list[str] = []

    if not nodes:
        errors.append("Workflow has no nodes")
        return errors

    # Detect multiple scheduler nodes
    scheduler_nodes = [n for n in nodes if n["type"] == SchedulerNode.NODE_TYPE]
    if len(scheduler_nodes) > 1:
        errors.append("Only one Scheduler node is allowed per workflow")

    # Per-node validation
    for node_data in nodes:
        try:
            node = _build_node(node_data)
            node_errors = node.validate()
            for err in node_errors:
                errors.append(f"[{node_data.get('label', node_data['id'])}] {err}")
        except ValueError as exc:
            errors.append(str(exc))

    # Try topological sort
    try:
        _topological_sort(nodes, edges)
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def generate_script(workflow_name: str, nodes: list[dict], edges: list[dict]) -> str:
    """
    Generate a standalone Python script from the workflow graph.
    Returns the script as a string.
    """
    errors = validate_graph(nodes, edges)
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    sorted_nodes = _topological_sort(nodes, edges)

    lines: list[str] = [SCRIPT_HEADER]
    lines.append(f'WORKFLOW_NAME = {repr(workflow_name)}\n')

    # Locate scheduler node (if any) — it must be first or the code wraps around it
    scheduler_idx: Optional[int] = None
    for i, node_data in enumerate(sorted_nodes):
        if node_data["type"] == SchedulerNode.NODE_TYPE:
            scheduler_idx = i
            break

    if scheduler_idx is not None:
        # Emit nodes before the scheduler (setup code, flat)
        for node_data in sorted_nodes[:scheduler_idx]:
            node = _build_node(node_data)
            lines.append(node.to_code(indent=0))
            lines.append("")

        # Emit the scheduler loop header
        sched_node = _build_node(sorted_nodes[scheduler_idx])
        lines.append(sched_node.to_code(indent=0))  # emits "while True:"
        lines.append("")

        # Emit the rest of the nodes inside the loop (indented 4 spaces)
        for node_data in sorted_nodes[scheduler_idx + 1:]:
            node = _build_node(node_data)
            lines.append(node.to_code(indent=4))
            lines.append("")

        # Close the loop with time.sleep
        lines.append(sched_node.loop_close_code(indent=0))  # already has 4-space indent inside
        lines.append("")

    else:
        # No scheduler — flat sequential execution
        for node_data in sorted_nodes:
            node = _build_node(node_data)
            lines.append(node.to_code(indent=0))
            lines.append("")

    lines.append('if __name__ == "__main__":')
    lines.append('    pass  # entry point')

    return "\n".join(lines)
