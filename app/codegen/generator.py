"""
Code Generator
==============
Takes a workflow graph (nodes + edges) and produces a standalone Python script
that can be compiled to an .exe with PyInstaller.

Execution order is determined via topological sort of the DAG formed by edges.
Nodes at the same topological level (independent branches) are executed in
parallel using concurrent.futures.ThreadPoolExecutor.
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
from concurrent.futures import ThreadPoolExecutor as _TPE, wait as _wait, ALL_COMPLETED as _ALL

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


def _topological_waves(nodes: list[dict], edges: list[dict]) -> list[list[dict]]:
    """
    Returns nodes grouped into execution waves using Kahn's BFS algorithm.

    Each wave is a list of nodes that can run concurrently — they share no
    dependency between each other within the same wave.  Waves must be executed
    in order: wave N must complete before wave N+1 starts.

    Raises ValueError if the graph contains a cycle.
    """
    node_map = {n["id"]: n for n in nodes}
    in_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        src = edge["source_node_id"]
        tgt = edge["target_node_id"]
        adjacency[src].append(tgt)
        in_degree[tgt] += 1

    # Seed with all nodes that have no predecessors
    current_wave_ids: list[str] = [
        node_id for node_id in node_map if in_degree[node_id] == 0
    ]
    waves: list[list[dict]] = []
    visited = 0

    while current_wave_ids:
        waves.append([node_map[nid] for nid in current_wave_ids])
        visited += len(current_wave_ids)
        next_wave_ids: list[str] = []
        for node_id in current_wave_ids:
            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_wave_ids.append(neighbor)
        current_wave_ids = next_wave_ids

    if visited != len(nodes):
        raise ValueError("Workflow contains a cycle — cannot generate code")

    return waves


def _emit_waves(
    waves: list[list[dict]],
    base_indent: int,
    lines: list[str],
) -> None:
    """
    Emit Python source lines for a sequence of waves at the given base indent.

    - A wave with a single node is emitted inline (no threading overhead).
    - A wave with multiple nodes is wrapped in a ThreadPoolExecutor block so
      all branches in that wave run concurrently.  Each branch is a nested
      function _wave_<w>_branch_<b>() to give it its own local scope.
      Any exception raised inside a branch is re-raised by _f.result(),
      which propagates up through _run() to the top-level error handler.
    """
    pad = " " * base_indent

    for w_idx, wave in enumerate(waves):
        if len(wave) == 1:
            # Single node — emit directly, no threading
            node = _build_node(wave[0])
            lines.append(node.to_code(indent=base_indent))
            lines.append("")
        else:
            # Multiple independent nodes — run in parallel
            branch_names: list[str] = []
            for b_idx, node_data in enumerate(wave):
                fn_name = f"_wave_{w_idx}_branch_{b_idx}"
                branch_names.append(fn_name)
                node = _build_node(node_data)
                # Define branch function at base_indent level
                lines.append(f"{pad}def {fn_name}():")
                lines.append(node.to_code(indent=base_indent + 4))
                lines.append("")

            # Dispatch all branches and wait; re-raise any exception
            submits = ", ".join(
                f"_pool.submit({fn})" for fn in branch_names
            )
            lines.append(f"{pad}with _TPE() as _pool:")
            lines.append(f"{pad}    _futs = [{submits}]")
            lines.append(f"{pad}    _done, _ = _wait(_futs, return_when=_ALL)")
            lines.append(f"{pad}    for _f in _done:")
            lines.append(f"{pad}        _f.result()  # re-raises branch exceptions")
            lines.append("")


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

    # Check for cycles via topological waves
    try:
        _topological_waves(nodes, edges)
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def generate_script(workflow_name: str, nodes: list[dict], edges: list[dict]) -> str:
    """
    Generate a standalone Python script from the workflow graph.
    Independent branches at the same topological level are executed in parallel.
    Returns the script as a string.
    """
    errors = validate_graph(nodes, edges)
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    waves = _topological_waves(nodes, edges)

    # WORKFLOW_NAME must be defined before the logging setup in SCRIPT_HEADER
    lines: list[str] = [f'WORKFLOW_NAME = {repr(workflow_name)}\n']
    lines.append(SCRIPT_HEADER)

    # Locate the wave that contains the Scheduler node (if any).
    # The scheduler must be alone in its wave (it opens the while-True block).
    scheduler_wave_idx: Optional[int] = None
    for w_idx, wave in enumerate(waves):
        for node_data in wave:
            if node_data["type"] == SchedulerNode.NODE_TYPE:
                scheduler_wave_idx = w_idx
                break
        if scheduler_wave_idx is not None:
            break

    # All workflow logic goes inside _run() so errors are caught at the top level
    lines.append(WORKFLOW_MAIN_START)  # "def _run():"

    if scheduler_wave_idx is not None:
        # Waves before the scheduler → setup code (indent=4, inside _run)
        _emit_waves(waves[:scheduler_wave_idx], base_indent=4, lines=lines)

        # Scheduler wave: find the node and emit the while-True header
        sched_wave = waves[scheduler_wave_idx]
        sched_node_data = next(
            nd for nd in sched_wave if nd["type"] == SchedulerNode.NODE_TYPE
        )
        sched_node = _build_node(sched_node_data)
        lines.append(sched_node.to_code(indent=4))  # "    while True:"
        lines.append("")

        # Waves after the scheduler → loop body (indent=8, inside while True)
        _emit_waves(waves[scheduler_wave_idx + 1:], base_indent=8, lines=lines)

        # Close the loop with time.sleep (indent=4 inside _run)
        lines.append(sched_node.loop_close_code(indent=4))
        lines.append("")

    else:
        # No scheduler — all waves run sequentially inside _run (indent=4)
        _emit_waves(waves, base_indent=4, lines=lines)

    lines.append(WORKFLOW_MAIN_END)

    return "\n".join(lines)
