from flask import Blueprint, request, jsonify, current_app
from app.db.manager import (
    list_workflows,
    get_workflow_meta,
    create_workflow,
    update_workflow_meta,
    delete_workflow,
    get_workflow_graph,
    save_workflow_graph,
)

workflows_bp = Blueprint("workflows", __name__)


def data_dir():
    return current_app.config["DATA_DIR"]


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
    return jsonify(get_workflow_graph(data_dir(), workflow_id))


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

    save_workflow_graph(data_dir(), workflow_id, nodes, edges)
    return jsonify({"ok": True})
