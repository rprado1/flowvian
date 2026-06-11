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
from app.nodes.subtract_time_from_date import SubtractTimeFromDateNode


NODE_REGISTRY: dict[str, type[BaseNode]] = {
    SchedulerNode.NODE_TYPE: SchedulerNode,
    SetVariablesNode.NODE_TYPE: SetVariablesNode,
    GetCurrentDateUTCNode.NODE_TYPE: GetCurrentDateUTCNode,
    AddTimeToDateNode.NODE_TYPE: AddTimeToDateNode,
    SubtractTimeFromDateNode.NODE_TYPE: SubtractTimeFromDateNode,
}

SCRIPT_HEADER = '''\
# ============================================================
# Auto-generated workflow script
# DO NOT EDIT MANUALLY
# ============================================================
import sys
import os
import logging
import traceback

# ---- Error log setup ----
# Log file is placed next to the .exe (or .py when running from source)
_exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))
_log_path = os.path.join(_exe_dir, WORKFLOW_NAME.replace(" ", "_") + "_errors.log")
logging.basicConfig(
    filename=_log_path,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger(__name__)
'''

WORKFLOW_MAIN_START = '''\
def _run():
'''

WORKFLOW_MAIN_END = '''\
if __name__ == "__main__":
    try:
        _run()
    except Exception as _exc:
        _logger.error("Unhandled exception:\\n%s", traceback.format_exc())
        print(f"ERROR: {_exc}  (see {_log_path})", file=sys.stderr)
        sys.exit(1)
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

    # WORKFLOW_NAME must be defined before the logging setup in SCRIPT_HEADER
    lines: list[str] = [f'WORKFLOW_NAME = {repr(workflow_name)}\n']
    lines.append(SCRIPT_HEADER)

    # Locate scheduler node (if any) — it must be first or the code wraps around it
    scheduler_idx: Optional[int] = None
    for i, node_data in enumerate(sorted_nodes):
        if node_data["type"] == SchedulerNode.NODE_TYPE:
            scheduler_idx = i
            break

    # All workflow logic goes inside _run() so errors are caught at the top level
    lines.append(WORKFLOW_MAIN_START)  # "def _run():"

    if scheduler_idx is not None:
        # Emit nodes before the scheduler (setup code, indented inside _run)
        for node_data in sorted_nodes[:scheduler_idx]:
            node = _build_node(node_data)
            lines.append(node.to_code(indent=4))
            lines.append("")

        # Emit the scheduler loop header (indented 4 inside _run)
        sched_node = _build_node(sorted_nodes[scheduler_idx])
        lines.append(sched_node.to_code(indent=4))  # emits "    while True:"
        lines.append("")

        # Emit the rest of the nodes inside the loop (indented 8 = 4 _run + 4 loop)
        for node_data in sorted_nodes[scheduler_idx + 1:]:
            node = _build_node(node_data)
            lines.append(node.to_code(indent=8))
            lines.append("")

        # Close the loop with time.sleep (indented 4 inside _run)
        lines.append(sched_node.loop_close_code(indent=4))
        lines.append("")

    else:
        # No scheduler — flat sequential execution inside _run
        for node_data in sorted_nodes:
            node = _build_node(node_data)
            lines.append(node.to_code(indent=4))
            lines.append("")

    lines.append(WORKFLOW_MAIN_END)

    return "\n".join(lines)
