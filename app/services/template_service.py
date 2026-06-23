from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.codegen.generator import validate_graph
from app.db.manager import create_workflow, save_workflow_graph
from app.security.secrets_crypto import SECRET_MASK, encrypt_secret_value, is_encrypted_secret_value

TEMPLATE_VERSION = "1.0"
MAX_TEMPLATE_BYTES = 1024 * 1024
MAX_NAME_LENGTH = 120
MAX_LABEL_LENGTH = 120


def _sanitize_text(value: Any, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


def _mask_secrets_in_nodes(nodes: List[dict]) -> List[dict]:
    out_nodes: List[dict] = []
    for raw_node in nodes:
        node = copy.deepcopy(raw_node if isinstance(raw_node, dict) else {})
        node_type = str(node.get("type") or "")
        cfg = node.get("config")
        config = cfg if isinstance(cfg, dict) else {}

        if node_type == "set_variables":
            variables = config.get("variables")
            if isinstance(variables, list):
                next_variables = []
                for raw_item in variables:
                    item = copy.deepcopy(raw_item if isinstance(raw_item, dict) else {})
                    item_type = str(item.get("type") or "string").strip().lower()
                    if item_type == "secret":
                        item["value"] = SECRET_MASK
                    next_variables.append(item)
                config["variables"] = next_variables

        node["config"] = config
        out_nodes.append(node)
    return out_nodes


def build_template_payload(meta: dict, graph: dict) -> dict:
    name = _sanitize_text(meta.get("name"), MAX_NAME_LENGTH) or "Imported workflow"
    nodes = graph.get("nodes", []) if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges", []) if isinstance(graph.get("edges"), list) else []

    sanitized_nodes = []
    for raw_node in nodes:
        node = raw_node if isinstance(raw_node, dict) else {}
        sanitized_nodes.append(
            {
                "id": str(node.get("id") or "").strip(),
                "type": str(node.get("type") or "").strip(),
                "label": _sanitize_text(node.get("label"), MAX_LABEL_LENGTH) or str(node.get("type") or ""),
                "pos_x": float(node.get("pos_x") or 0),
                "pos_y": float(node.get("pos_y") or 0),
                "config": copy.deepcopy(node.get("config") if isinstance(node.get("config"), dict) else {}),
            }
        )

    sanitized_edges = []
    for raw_edge in edges:
        edge = raw_edge if isinstance(raw_edge, dict) else {}
        sanitized_edges.append(
            {
                "id": str(edge.get("id") or "").strip(),
                "source_node_id": str(edge.get("source_node_id") or "").strip(),
                "target_node_id": str(edge.get("target_node_id") or "").strip(),
                "source_output": str(edge.get("source_output") or "output_1").strip() or "output_1",
                "target_input": str(edge.get("target_input") or "input_1").strip() or "input_1",
            }
        )

    return {
        "template_version": TEMPLATE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "workflow": {
            "name": name,
            "nodes": _mask_secrets_in_nodes(sanitized_nodes),
            "edges": sanitized_edges,
        },
    }


def _prepare_secret_values(nodes: List[dict]) -> Tuple[List[dict], List[str]]:
    warnings: List[str] = []
    next_nodes: List[dict] = []

    for raw_node in nodes:
        node = copy.deepcopy(raw_node if isinstance(raw_node, dict) else {})
        node_type = str(node.get("type") or "")
        cfg = node.get("config")
        config = cfg if isinstance(cfg, dict) else {}

        if node_type == "set_variables":
            variables = config.get("variables")
            if isinstance(variables, list):
                next_variables = []
                for raw_item in variables:
                    item = copy.deepcopy(raw_item if isinstance(raw_item, dict) else {})
                    item_type = str(item.get("type") or "string").strip().lower()
                    if item_type == "secret":
                        raw_value = item.get("value", "")
                        value = str(raw_value) if raw_value is not None else ""
                        if value == SECRET_MASK:
                            item["value"] = ""
                            key_name = str(item.get("key") or "").strip() or "(unnamed)"
                            warnings.append(
                                f"Secret '{key_name}' was exported masked and imported empty. Set its value manually."
                            )
                        elif value and not is_encrypted_secret_value(value):
                            item["value"] = encrypt_secret_value(value)
                    next_variables.append(item)
                config["variables"] = next_variables

        node["config"] = config
        next_nodes.append(node)

    return next_nodes, warnings


def validate_and_sanitize_template(payload: Any) -> Tuple[Optional[dict], List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(payload, dict):
        return None, ["Template payload must be a JSON object"], warnings

    version = str(payload.get("template_version") or "").strip()
    if version != TEMPLATE_VERSION:
        errors.append(f"Unsupported template_version '{version}'. Expected '{TEMPLATE_VERSION}'")

    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        errors.append("Template must include a 'workflow' object")
        return None, errors, warnings

    name = _sanitize_text(workflow.get("name"), MAX_NAME_LENGTH)
    if not name:
        name = "Imported workflow"

    raw_nodes = workflow.get("nodes")
    raw_edges = workflow.get("edges")
    if not isinstance(raw_nodes, list):
        errors.append("workflow.nodes must be a list")
        raw_nodes = []
    if not isinstance(raw_edges, list):
        errors.append("workflow.edges must be a list")
        raw_edges = []

    nodes: List[dict] = []
    node_ids: set[str] = set()
    for idx, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, dict):
            errors.append(f"workflow.nodes[{idx}] must be an object")
            continue

        node_id = str(raw_node.get("id") or "").strip()
        node_type = str(raw_node.get("type") or "").strip()
        config = raw_node.get("config") if isinstance(raw_node.get("config"), dict) else {}
        if not node_id:
            errors.append(f"workflow.nodes[{idx}] missing id")
            continue
        if node_id in node_ids:
            errors.append(f"workflow.nodes[{idx}] duplicated id '{node_id}'")
            continue
        if not node_type:
            errors.append(f"workflow.nodes[{idx}] missing type")
            continue

        node_ids.add(node_id)
        label = _sanitize_text(raw_node.get("label"), MAX_LABEL_LENGTH) or node_type
        try:
            pos_x = float(raw_node.get("pos_x") or 0)
            pos_y = float(raw_node.get("pos_y") or 0)
        except Exception:
            errors.append(f"workflow.nodes[{idx}] has invalid position values")
            continue

        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "label": label,
                "pos_x": pos_x,
                "pos_y": pos_y,
                "config": copy.deepcopy(config),
            }
        )

    edges: List[dict] = []
    edge_ids: set[str] = set()
    for idx, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, dict):
            errors.append(f"workflow.edges[{idx}] must be an object")
            continue

        edge_id = str(raw_edge.get("id") or "").strip()
        src = str(raw_edge.get("source_node_id") or "").strip()
        tgt = str(raw_edge.get("target_node_id") or "").strip()

        if not edge_id:
            errors.append(f"workflow.edges[{idx}] missing id")
            continue
        if edge_id in edge_ids:
            errors.append(f"workflow.edges[{idx}] duplicated id '{edge_id}'")
            continue
        if not src or not tgt:
            errors.append(f"workflow.edges[{idx}] requires source_node_id and target_node_id")
            continue
        if src not in node_ids:
            errors.append(f"workflow.edges[{idx}] source node '{src}' does not exist")
            continue
        if tgt not in node_ids:
            errors.append(f"workflow.edges[{idx}] target node '{tgt}' does not exist")
            continue

        edge_ids.add(edge_id)
        edges.append(
            {
                "id": edge_id,
                "source_node_id": src,
                "target_node_id": tgt,
                "source_output": str(raw_edge.get("source_output") or "output_1").strip() or "output_1",
                "target_input": str(raw_edge.get("target_input") or "input_1").strip() or "input_1",
            }
        )

    if not nodes:
        errors.append("workflow.nodes must include at least one node")

    graph_errors = validate_graph(nodes, edges)
    if graph_errors:
        errors.extend(graph_errors)

    if errors:
        return None, errors, warnings

    prepared_nodes, secret_warnings = _prepare_secret_values(nodes)
    warnings.extend(secret_warnings)

    sanitized = {
        "template_version": TEMPLATE_VERSION,
        "workflow": {
            "name": name,
            "nodes": prepared_nodes,
            "edges": edges,
        },
    }
    return sanitized, errors, warnings


def import_template_as_workflow(data_dir: str, sanitized_template: dict) -> dict:
    workflow_obj = sanitized_template.get("workflow") if isinstance(sanitized_template, dict) else {}
    wf = workflow_obj if isinstance(workflow_obj, dict) else {}

    name = _sanitize_text(wf.get("name"), MAX_NAME_LENGTH) or "Imported workflow"
    description = "Imported from template"
    created = create_workflow(data_dir, name, description)

    nodes = wf.get("nodes") if isinstance(wf.get("nodes"), list) else []
    edges = wf.get("edges") if isinstance(wf.get("edges"), list) else []
    save_workflow_graph(data_dir, created["id"], nodes, edges)
    return created
