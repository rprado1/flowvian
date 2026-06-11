import os
import subprocess
import tempfile

from flask import Blueprint, jsonify, current_app, send_file
from app.db.manager import get_workflow_meta, get_workflow_graph
from app.codegen.generator import generate_script, validate_graph

builder_bp = Blueprint("builder", __name__)


def data_dir():
    return current_app.config["DATA_DIR"]


def output_dir():
    return current_app.config["OUTPUT_DIR"]


@builder_bp.route("/<workflow_id>/validate", methods=["POST"])
def validate(workflow_id):
    """Validate the workflow graph without building."""
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    graph = get_workflow_graph(data_dir(), workflow_id)
    errors = validate_graph(graph["nodes"], graph["edges"])
    if errors:
        return jsonify({"valid": False, "errors": errors}), 422
    return jsonify({"valid": True, "errors": []})


@builder_bp.route("/<workflow_id>/preview", methods=["POST"])
def preview(workflow_id):
    """Return the generated Python source without compiling."""
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    graph = get_workflow_graph(data_dir(), workflow_id)
    try:
        script = generate_script(meta["name"], graph["nodes"], graph["edges"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify({"script": script})


@builder_bp.route("/<workflow_id>/build", methods=["POST"])
def build(workflow_id):
    """
    Generate Python script and compile it to a Windows .exe using PyInstaller.
    Returns JSON with the build log and, on success, a download_url.
    """
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    graph = get_workflow_graph(data_dir(), workflow_id)

    # 1. Generate Python source
    try:
        script = generate_script(meta["name"], graph["nodes"], graph["edges"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    # 2. Write script to a temp file inside output_dir
    wf_output_dir = os.path.join(output_dir(), workflow_id)
    os.makedirs(wf_output_dir, exist_ok=True)

    safe_name = _safe_filename(meta["name"])
    script_path = os.path.join(wf_output_dir, f"{safe_name}.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    # 3. Run PyInstaller
    dist_dir = os.path.join(wf_output_dir, "dist")
    work_dir = os.path.join(wf_output_dir, "build")
    spec_dir = wf_output_dir

    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconfirm",
        "--distpath", dist_dir,
        "--workpath", work_dir,
        "--specpath", spec_dir,
        "--name", safe_name,
        script_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "PyInstaller timed out (>5 min)"}), 500
    except FileNotFoundError:
        return jsonify({"error": "pyinstaller not found — run: pip install pyinstaller"}), 500

    log = result.stdout + result.stderr

    if result.returncode != 0:
        return jsonify({"error": "PyInstaller failed", "log": log}), 500

    exe_path = os.path.join(dist_dir, f"{safe_name}.exe")
    if not os.path.exists(exe_path):
        return jsonify({"error": "Build succeeded but .exe not found", "log": log}), 500

    return jsonify({
        "ok": True,
        "log": log,
        "exe_name": f"{safe_name}.exe",
        "download_url": f"/api/workflows/{workflow_id}/download",
    })


@builder_bp.route("/<workflow_id>/download", methods=["GET"])
def download(workflow_id):
    """Download the compiled .exe for a workflow."""
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    safe_name = _safe_filename(meta["name"])
    exe_path = os.path.join(output_dir(), workflow_id, "dist", f"{safe_name}.exe")

    if not os.path.exists(exe_path):
        return jsonify({"error": "No compiled .exe found — build the workflow first"}), 404

    return send_file(exe_path, as_attachment=True, download_name=f"{safe_name}.exe")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Convert a workflow name to a safe filename (no spaces or special chars)."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return safe.strip("_") or "workflow"
