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
from typing import Optional, cast
from app.nodes.base import BaseNode
from app.nodes.scheduler import SchedulerNode
from app.nodes.set_variables import SetVariablesNode
from app.nodes.get_current_date import GetCurrentDateUTCNode
from app.nodes.add_time_to_date import AddTimeToDateNode
from app.nodes.merge import MergeNode
from app.nodes.subtract_time_from_date import SubtractTimeFromDateNode


NODE_REGISTRY: dict[str, type[BaseNode]] = {
    SchedulerNode.NODE_TYPE: SchedulerNode,
    SetVariablesNode.NODE_TYPE: SetVariablesNode,
    GetCurrentDateUTCNode.NODE_TYPE: GetCurrentDateUTCNode,
    AddTimeToDateNode.NODE_TYPE: AddTimeToDateNode,
    MergeNode.NODE_TYPE: MergeNode,
    SubtractTimeFromDateNode.NODE_TYPE: SubtractTimeFromDateNode,
}

SCRIPT_HEADER = '''\
# ============================================================
# Auto-generated workflow script
# DO NOT EDIT MANUALLY
# ============================================================
import sys
import os
import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
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
    global _items
'''

WORKFLOW_MAIN_END = '''\
if __name__ == "__main__":
    try:
        _run()
    except Exception as _exc:
        _logger.error("Unhandled exception:\\n%s", traceback.format_exc())
        print(f"ERROR: {_exc}  (see {_log_path})", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(_items, default=str))
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
    edges: list[dict],
    base_indent: int,
    lines: list[str],
    instrument: bool = False,
) -> None:
    """
    Emit Python source lines for a sequence of waves at the given base indent.

    - A wave with a single node is emitted inline (no threading overhead).
    - A wave with multiple nodes is wrapped in a ThreadPoolExecutor block so
      all branches in that wave run concurrently. Each branch resolves its own
      input from predecessor node outputs.
    - Branches stay isolated until an explicit merge node combines them.
    - When instrument=True, each node's execution is wrapped with items snapshot
      that appends a trace entry to the global _trace list.
    """
    if not waves:
        return

    subset_nodes = [node_data for wave in waves for node_data in wave]
    subset_node_ids = [node_data["id"] for node_data in subset_nodes]
    subset_node_ids_set = set(subset_node_ids)

    incoming_map: dict[str, list[str]] = {node_id: [] for node_id in subset_node_ids}
    outgoing_internal_count: dict[str, int] = {node_id: 0 for node_id in subset_node_ids}
    for edge in edges:
        src = edge["source_node_id"]
        tgt = edge["target_node_id"]
        if src in subset_node_ids_set and tgt in subset_node_ids_set:
            if src not in incoming_map[tgt]:
                incoming_map[tgt].append(src)
            outgoing_internal_count[src] += 1

    terminal_node_ids = [
        node_id for node_id in subset_node_ids if outgoing_internal_count[node_id] == 0
    ]

    pad = " " * base_indent
    lines.append(f"{pad}_items_seed = list(_items)")
    lines.append(f"{pad}_node_items = {{}}")
    lines.append("")

    def _emit_node_input_setup(node_data: dict, indent: int) -> list[str]:
        node_id = node_data["id"]
        preds = incoming_map.get(node_id, [])
        line_prefix = " " * indent
        out: list[str] = []

        if not preds:
            out.append(f"{line_prefix}_items = list(_items_seed)")
            return out

        if len(preds) == 1:
            out.append(f"{line_prefix}_items = list(_node_items.get({preds[0]!r}, []))")
            return out

        if node_data["type"] == MergeNode.NODE_TYPE:
            out.append(f"{line_prefix}_items = []")
            for pred in preds:
                out.append(f"{line_prefix}_items.extend(list(_node_items.get({pred!r}, [])))")
            return out

        out.append(f"{line_prefix}_items = list(_node_items.get({preds[0]!r}, []))")
        return out

    for w_idx, wave in enumerate(waves):
        if len(wave) == 1:
            node_data = wave[0]
            node = _build_node(node_data)
            node_id = node_data["id"]
            node_type = node_data["type"]
            node_label = node_data.get("label", node_type)

            # Scheduler nodes don't use the item loop pattern
            if node_type == SchedulerNode.NODE_TYPE:
                lines.append(node.to_code(indent=base_indent))
                lines.append("")
                continue

            lines.extend(_emit_node_input_setup(node_data, base_indent))

            if instrument:
                lines.append(f"{pad}_items_before = list(_items)")
                lines.append(f"{pad}try:")
                lines.append(node.to_code(indent=base_indent + 4))
                lines.append(f"{pad}    _items_after = list(_items)")
                lines.append(f"{pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'ok', 'ts': time.time(), 'items_in': _items_before, 'items_out': _items_after}})")
                lines.append(f"{pad}    _node_items[{node_id!r}] = _items_after")
                lines.append(f"{pad}except Exception as _tr_ex:")
                lines.append(f"{pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'error', 'ts': time.time(), 'items_in': _items_before, 'error': str(_tr_ex)}})")
                lines.append(f"{pad}    raise")
                lines.append("")
            else:
                lines.append(node.to_code(indent=base_indent))
                lines.append(f"{pad}_node_items[{node_id!r}] = list(_items)")
                lines.append("")
        else:
            # Multi-node wave: each branch resolves inputs from its own predecessors.
            branch_names: list[str] = []
            lines.append(f"{pad}_wave_{w_idx}_results = [None] * {len(wave)}")
            for b_idx, node_data in enumerate(wave):
                fn_name = f"_wave_{w_idx}_branch_{b_idx}"
                branch_names.append(fn_name)
                node = _build_node(node_data)
                node_id = node_data["id"]
                node_type = node_data["type"]
                node_label = node_data.get("label", node_type)

                lines.append(f"{pad}def {fn_name}():")

                lines.extend(_emit_node_input_setup(node_data, base_indent + 4))
                inner_pad = " " * (base_indent + 4)

                if instrument:
                    lines.append(f"{inner_pad}_items_before = list(_items)")
                    lines.append(f"{inner_pad}try:")
                    lines.append(node.to_code(indent=base_indent + 8))
                    lines.append(f"{inner_pad}    _items_after = list(_items)")
                    lines.append(f"{inner_pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'ok', 'ts': time.time(), 'items_in': _items_before, 'items_out': _items_after}})")
                    lines.append(f"{inner_pad}    _wave_{w_idx}_results[{b_idx}] = _items_after")
                    lines.append(f"{inner_pad}except Exception as _tr_ex:")
                    lines.append(f"{inner_pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'error', 'ts': time.time(), 'items_in': _items_before, 'error': str(_tr_ex)}})")
                    lines.append(f"{inner_pad}    raise")
                else:
                    lines.append(node.to_code(indent=base_indent + 4))
                    lines.append(f"{inner_pad}_wave_{w_idx}_results[{b_idx}] = list(_items)")
                lines.append("")

            submits = ", ".join(
                f"_pool.submit({fn})" for fn in branch_names
            )
            lines.append(f"{pad}with _TPE() as _pool:")
            lines.append(f"{pad}    _futs = [{submits}]")
            lines.append(f"{pad}    _done, _ = _wait(_futs, return_when=_ALL)")
            lines.append(f"{pad}    for _f in _done:")
            lines.append(f"{pad}        _f.result()  # re-raises branch exceptions")
            for b_idx, node_data in enumerate(wave):
                node_id = node_data["id"]
                lines.append(
                    f"{pad}_node_items[{node_id!r}] = _wave_{w_idx}_results[{b_idx}] or []"
                )
            lines.append("")

    if terminal_node_ids:
        lines.append(f"{pad}_items = []")
        for node_id in terminal_node_ids:
            lines.append(f"{pad}_items.extend(list(_node_items.get({node_id!r}, [])))")
    else:
        lines.append(f"{pad}_items = list(_items_seed)")
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

    incoming_count: dict[str, int] = defaultdict(int)
    for edge in edges:
        incoming_count[edge["target_node_id"]] += 1

    for node_data in nodes:
        node_id = node_data["id"]
        if incoming_count[node_id] > 1 and node_data["type"] != MergeNode.NODE_TYPE:
            errors.append(
                f"[{node_data.get('label', node_id)}] "
                f"Only 'merge' nodes can have multiple incoming edges "
                f"(has {incoming_count[node_id]})"
            )

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


def generate_script(workflow_name: str, workflow_id: str, nodes: list[dict], edges: list[dict]) -> str:
    """
    Generate a standalone Python script from the workflow graph.
    Independent branches at the same topological level are executed in parallel.
    Returns the script as a string.
    """
    errors = validate_graph(nodes, edges)
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    waves = _topological_waves(nodes, edges)

    # WORKFLOW_NAME and WORKFLOW_ID must be defined before the logging setup in SCRIPT_HEADER
    lines: list[str] = [
        f'WORKFLOW_NAME = {repr(workflow_name)}',
        f'WORKFLOW_ID = {repr(workflow_id)}\n',
    ]
    lines.append(SCRIPT_HEADER)

    # Initialize _items array with workflow context
    lines.append("# ---- Initialize items array ----")
    lines.append("EXECUTION_ID = str(uuid.uuid4())")
    lines.append("_items = [{")
    lines.append('    "workflowId": WORKFLOW_ID,')
    lines.append('    "executionId": EXECUTION_ID,')
    lines.append('    "executionDate": datetime.now(timezone.utc).isoformat()')
    lines.append("}]\n")

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
        _emit_waves(waves[:scheduler_wave_idx], edges=edges, base_indent=4, lines=lines)

        # Scheduler wave: find the node and emit the while-True header
        sched_wave = waves[scheduler_wave_idx]
        sched_node_data = next(
            nd for nd in sched_wave if nd["type"] == SchedulerNode.NODE_TYPE
        )
        sched_node = cast(SchedulerNode, _build_node(sched_node_data))
        lines.append(sched_node.to_code(indent=4))  # "    while True:"
        lines.append("")

        # Waves after the scheduler → loop body (indent=8, inside while True)
        _emit_waves(waves[scheduler_wave_idx + 1:], edges=edges, base_indent=8, lines=lines)

        # Close the loop with time.sleep (indent=4 inside _run)
        lines.append(sched_node.loop_close_code(indent=4))
        lines.append("        print(json.dumps(_items, default=str))")
        lines.append("")

    else:
        # No scheduler — all waves run sequentially inside _run (indent=4)
        _emit_waves(waves, edges=edges, base_indent=4, lines=lines)

    lines.append(WORKFLOW_MAIN_END)

    return "\n".join(lines)


RUN_SCRIPT_HEADER = '''\
# ============================================================
# Auto-generated workflow run script (instrumented)
# ============================================================
import sys
import os
import json
import time
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor as _TPE, wait as _wait, ALL_COMPLETED as _ALL

_trace = []
_trace_path = os.environ.get("WORKFLOW_TRACE_PATH", "")

def _write_traces():
    if _trace_path:
        try:
            with open(_trace_path, "w", encoding="utf-8") as _f:
                json.dump(_trace, _f, default=str, indent=2)
        except Exception:
            pass
'''


def generate_run_script(workflow_name: str, workflow_id: str, nodes: list[dict], edges: list[dict]) -> str:
    """
    Generate an instrumented Python script for one-time workflow execution.
    Each node's input/output items are captured and written to a trace file.

    The trace file path is passed via the WORKFLOW_TRACE_PATH environment variable.
    Returns the script as a string.
    """
    errors = validate_graph(nodes, edges)
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    waves = _topological_waves(nodes, edges)

    lines: list[str] = [
        f'WORKFLOW_NAME = {repr(workflow_name)}',
        f'WORKFLOW_ID = {repr(workflow_id)}\n',
    ]
    lines.append(RUN_SCRIPT_HEADER)

    # Initialize _items array with workflow context
    lines.append("# ---- Initialize items array ----")
    lines.append("EXECUTION_ID = str(uuid.uuid4())")
    lines.append("_items = [{")
    lines.append('    "workflowId": WORKFLOW_ID,')
    lines.append('    "executionId": EXECUTION_ID,')
    lines.append('    "executionDate": datetime.now(timezone.utc).isoformat()')
    lines.append("}]\n")

    scheduler_wave_idx: Optional[int] = None
    for w_idx, wave in enumerate(waves):
        for node_data in wave:
            if node_data["type"] == SchedulerNode.NODE_TYPE:
                scheduler_wave_idx = w_idx
                break
        if scheduler_wave_idx is not None:
            break

    lines.append("def _run():")
    lines.append("    global _trace, _items")
    lines.append("")

    if scheduler_wave_idx is not None:
        _emit_waves(waves[:scheduler_wave_idx], edges=edges, base_indent=4, lines=lines,
                      instrument=True)

        sched_wave = waves[scheduler_wave_idx]
        sched_node_data = next(
            nd for nd in sched_wave if nd["type"] == SchedulerNode.NODE_TYPE
        )
        sched_node = _build_node(sched_node_data)
        node_id = sched_node_data["id"]
        node_type = sched_node_data["type"]
        node_label = sched_node_data.get("label", node_type)

        lines.append(f"    _items_before = list(_items)")
        lines.append("    try:")
        lines.append("        for _run_iter in range(1):")
        lines.append(f"            _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'ok', 'ts': time.time(), 'items_in': _items_before, 'items_out': list(_items)}})")

        _emit_waves(waves[scheduler_wave_idx + 1:], edges=edges, base_indent=8, lines=lines,
                      instrument=True)

        lines.append("    except Exception as _tr_ex:")
        lines.append(f"        _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'error', 'items_in': _items_before, 'error': str(_tr_ex)}})")
        lines.append("        raise")
        lines.append("")
    else:
        _emit_waves(waves, edges=edges, base_indent=4, lines=lines, instrument=True)

    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    try:")
    lines.append("        _run()")
    lines.append("    except Exception as _tr_ex:")
    lines.append("        if not _trace or _trace[-1].get('status') != 'error':")
    lines.append("            _trace.append({'status': 'fatal', 'error': str(_tr_ex)})")
    lines.append("    finally:")
    lines.append("        _write_traces()")
    lines.append("    print(json.dumps(_items, default=str))")

    return "\n".join(lines)
