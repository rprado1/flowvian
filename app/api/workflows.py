from flask import Blueprint, request, jsonify, current_app
from typing import Any
from app.db.manager import (
    list_workflows,
    get_workflow_meta,
    create_workflow,
    update_workflow_meta,
    delete_workflow,
    get_workflow_graph,
    save_workflow_graph,
)
from app.security.secrets_crypto import (
    SECRET_MASK,
    encrypt_secret_value,
    is_encrypted_secret_value,
    mask_secret_in_config,
)

workflows_bp = Blueprint("workflows", __name__)


def data_dir():
    return current_app.config["DATA_DIR"]


def _normalize_type(value) -> str:
    return str(value or "string").strip().lower() or "string"


def _encrypt_secrets_in_nodes(nodes: list[dict]) -> list[dict]:
    next_nodes = []
    for node in nodes:
        node_type = str(node.get("type") or "")
        raw_config = node.get("config")
        config: dict[str, Any] = raw_config if isinstance(raw_config, dict) else {}
        if node_type != "set_variables":
            next_nodes.append({**node, "config": config})
            continue

        variables = config.get("variables", [])
        if not isinstance(variables, list):
            next_nodes.append({**node, "config": config})
            continue

        next_variables = []
        for item in variables:
            if not isinstance(item, dict):
                next_variables.append(item)
                continue

            next_item = dict(item)
            if _normalize_type(next_item.get("type")) != "secret":
                next_variables.append(next_item)
                continue

            raw_value = next_item.get("value", "")
            if isinstance(raw_value, str):
                if raw_value == SECRET_MASK:
                    pass
                elif not is_encrypted_secret_value(raw_value):
                    next_item["value"] = encrypt_secret_value(raw_value)
            next_variables.append(next_item)

        next_config: dict[str, Any] = dict(config)
        next_config["variables"] = next_variables
        next_nodes.append({**node, "config": next_config})

    return next_nodes


def _mask_secrets_in_nodes(nodes: list[dict]) -> list[dict]:
    masked = []
    for node in nodes:
        node_type = str(node.get("type") or "")
        raw_config = node.get("config")
        config: dict[str, Any] = raw_config if isinstance(raw_config, dict) else {}
        if node_type == "set_variables":
            config = mask_secret_in_config(config)
        masked.append({**node, "config": config})
    return masked


# ---------------------------------------------------------------------------
# Workflow CRUD
# ---------------------------------------------------------------------------

@workflows_bp.route("/", methods=["GET"])
def list_all():
    return jsonify(list_workflows(data_dir()))


@workflows_bp.route("/", methods=["POST"])
def create():
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    description = (body.get("description") or "").strip()
    workflow = create_workflow(data_dir(), name, description)
    return jsonify(workflow), 201


@workflows_bp.route("/<workflow_id>", methods=["GET"])
def get_one(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404
    graph = get_workflow_graph(data_dir(), workflow_id)
    graph["nodes"] = _mask_secrets_in_nodes(graph.get("nodes", []))
    return jsonify({**meta, **graph})


@workflows_bp.route("/<workflow_id>", methods=["PUT"])
def update(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    name = (body.get("name") or meta["name"]).strip()
    description = (body.get("description") or meta.get("description", "")).strip()
    updated = update_workflow_meta(data_dir(), workflow_id, name, description)
    return jsonify(updated)


@workflows_bp.route("/<workflow_id>", methods=["DELETE"])
def delete(workflow_id):
    ok = delete_workflow(data_dir(), workflow_id)
    if not ok:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Graph (nodes + edges) save/load
# ---------------------------------------------------------------------------

@workflows_bp.route("/<workflow_id>/graph", methods=["GET"])
def get_graph(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404
    graph = get_workflow_graph(data_dir(), workflow_id)
    graph["nodes"] = _mask_secrets_in_nodes(graph.get("nodes", []))
    return jsonify(graph)


@workflows_bp.route("/<workflow_id>/graph", methods=["POST"])
def save_graph(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    nodes = body.get("nodes", [])
    edges = body.get("edges", [])

    # Basic validation
    for node in nodes:
        if not node.get("id") or not node.get("type"):
            return jsonify({"error": "each node must have id and type"}), 400
    for edge in edges:
        if not edge.get("id") or not edge.get("source_node_id") or not edge.get("target_node_id"):
            return jsonify({"error": "each edge must have id, source_node_id and target_node_id"}), 400

    current_graph = get_workflow_graph(data_dir(), workflow_id)
    existing_nodes = current_graph.get("nodes", [])
    existing_by_id = {str(n.get("id")): n for n in existing_nodes}

    prepared_nodes = []
    for node in nodes:
        node_type = str(node.get("type") or "")
        if node_type != "set_variables":
            prepared_nodes.append(node)
            continue

        config: dict[str, Any] = node.get("config") if isinstance(node.get("config"), dict) else {}
        variables = config.get("variables", [])
        if not isinstance(variables, list):
            prepared_nodes.append({**node, "config": config})
            continue

        previous = existing_by_id.get(str(node.get("id")), {})
        prev_config = previous.get("config") if isinstance(previous.get("config"), dict) else {}
        prev_variables = prev_config.get("variables", []) if isinstance(prev_config.get("variables"), list) else []
        prev_secret_map: dict[str, str] = {}
        for item in prev_variables:
            if not isinstance(item, dict):
                continue
            if _normalize_type(item.get("type")) != "secret":
                continue
            key = str(item.get("key") or "").strip()
            value = item.get("value", "")
            if key and isinstance(value, str) and value:
                prev_secret_map[key] = value

        next_variables = []
        for idx, item in enumerate(variables):
            if not isinstance(item, dict):
                next_variables.append(item)
                continue
            next_item = dict(item)
            if _normalize_type(next_item.get("type")) != "secret":
                next_variables.append(next_item)
                continue

            key = str(next_item.get("key") or "").strip()
            value = next_item.get("value", "")
            if value == SECRET_MASK:
                if key in prev_secret_map:
                    next_item["value"] = prev_secret_map[key]
                elif idx < len(prev_variables):
                    prev_item = prev_variables[idx]
                    if isinstance(prev_item, dict) and _normalize_type(prev_item.get("type")) == "secret":
                        prev_value = prev_item.get("value", "")
                        if isinstance(prev_value, str) and prev_value:
                            next_item["value"] = prev_value
            next_variables.append(next_item)

        next_config: dict[str, Any] = dict(config)
        next_config["variables"] = next_variables
        prepared_nodes.append({**node, "config": next_config})

    try:
        encrypted_nodes = _encrypt_secrets_in_nodes(prepared_nodes)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    save_workflow_graph(data_dir(), workflow_id, encrypted_nodes, edges)
    return jsonify({"ok": True})
