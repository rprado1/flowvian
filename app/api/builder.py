from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid

from flask import Blueprint, jsonify, current_app, send_file
from app.db.manager import get_workflow_meta, get_workflow_graph
from app.codegen.generator import generate_script, validate_graph, generate_run_script

builder_bp = Blueprint("builder", __name__)


def data_dir():
    return current_app.config["DATA_DIR"]


def output_dir():
    return current_app.config["OUTPUT_DIR"]


# ---------------------------------------------------------------------------
# Job persistence helpers  (files on disk — survive multi-process reloader)
# ---------------------------------------------------------------------------

def _job_path(wf_output_dir: str, job_id: str) -> str:
    return os.path.join(wf_output_dir, f"job_{job_id}.json")


def _write_job(wf_output_dir: str, job_id: str, payload: dict) -> None:
    path = _job_path(wf_output_dir, job_id)
    tmp  = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, path)   # atomic on same filesystem


def _read_job(wf_output_dir: str, job_id: str) -> dict | None:
    path = _job_path(wf_output_dir, job_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

@builder_bp.route("/<workflow_id>/validate", methods=["POST"])
def validate(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    graph  = get_workflow_graph(data_dir(), workflow_id)
    errors = validate_graph(graph["nodes"], graph["edges"])
    if errors:
        return jsonify({"valid": False, "errors": errors}), 422
    return jsonify({"valid": True, "errors": []})


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

@builder_bp.route("/<workflow_id>/preview", methods=["POST"])
def preview(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    graph = get_workflow_graph(data_dir(), workflow_id)
    try:
        script = generate_script(meta["name"], graph["nodes"], graph["edges"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify({"script": script})


# ---------------------------------------------------------------------------
# Build  (async — returns job_id immediately)
# ---------------------------------------------------------------------------

@builder_bp.route("/<workflow_id>/build", methods=["POST"])
def build(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    graph = get_workflow_graph(data_dir(), workflow_id)

    try:
        script = generate_script(meta["name"], graph["nodes"], graph["edges"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    wf_output_dir = os.path.join(output_dir(), workflow_id)
    os.makedirs(wf_output_dir, exist_ok=True)

    safe_name   = _safe_filename(meta["name"])
    script_path = os.path.join(wf_output_dir, f"{safe_name}.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    job_id   = uuid.uuid4().hex
    job_file = _job_path(wf_output_dir, job_id)
    _write_job(wf_output_dir, job_id, {"status": "running", "log": "", "error": None})

    dist_dir = os.path.join(wf_output_dir, "dist")
    work_dir = os.path.join(wf_output_dir, "build")
    spec_dir = wf_output_dir

    # Launch build_worker as a completely independent process so it survives
    # the Werkzeug reloader restarting the Flask worker.
    subprocess.Popen(
        [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "build_worker.py"),
            job_file, script_path, safe_name, dist_dir, work_dir, spec_dir,
        ],
        # Detach from parent's stdin/stdout so the process is truly independent
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )

    return jsonify({"job_id": job_id}), 202


@builder_bp.route("/<workflow_id>/build/status/<job_id>", methods=["GET"])
def build_status(workflow_id, job_id):
    wf_output_dir = os.path.join(output_dir(), workflow_id)
    job = _read_job(wf_output_dir, job_id)

    if job is None:
        return jsonify({"error": "job not found"}), 404

    if job["status"] == "running":
        return jsonify({"status": "running"})

    if job["status"] == "error":
        return jsonify({
            "status": "error",
            "error":  job["error"],
            "log":    job["log"],
        })

    return jsonify({
        "status":       "success",
        "log":          job["log"],
        "exe_name":     job["exe_name"],
        "download_url": f"/api/workflows/{workflow_id}/download",
    })


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

@builder_bp.route("/<workflow_id>/download", methods=["GET"])
def download(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    safe_name = _safe_filename(meta["name"])
    exe_path  = os.path.join(output_dir(), workflow_id, "dist", f"{safe_name}.exe")

    if not os.path.exists(exe_path):
        return jsonify({"error": "No compiled .exe found — build the workflow first"}), 404

    return send_file(exe_path, as_attachment=True, download_name=f"{safe_name}.exe")


# ---------------------------------------------------------------------------
# Run — execute workflow in-process and return per-node traces
# ---------------------------------------------------------------------------

@builder_bp.route("/<workflow_id>/run", methods=["POST"])
def run_workflow(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    graph = get_workflow_graph(data_dir(), workflow_id)

    try:
        script = generate_run_script(meta["name"], graph["nodes"], graph["edges"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    wf_output_dir = os.path.join(output_dir(), workflow_id)
    os.makedirs(wf_output_dir, exist_ok=True)

    run_script_path = os.path.join(wf_output_dir, "_run.py")
    trace_path = os.path.join(wf_output_dir, "_trace.json")

    with open(run_script_path, "w", encoding="utf-8") as f:
        f.write(script)

    env = os.environ.copy()
    env["WORKFLOW_TRACE_PATH"] = trace_path

    try:
        result = subprocess.run(
            [sys.executable, run_script_path],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return jsonify({
            "error": "Workflow execution timed out (30s)",
            "traces": [],
            "output": "",
        }), 500
    except Exception as exc:
        return jsonify({
            "error": f"Failed to execute workflow: {exc}",
            "traces": [],
            "output": "",
        }), 500

    traces = []
    if os.path.exists(trace_path):
        try:
            with open(trace_path, "r", encoding="utf-8") as f:
                traces = json.load(f)
        except Exception:
            pass

    output = result.stderr + result.stdout

    if result.returncode != 0:
        return jsonify({
            "error": f"Script exited with code {result.returncode}",
            "traces": traces,
            "output": output.strip() or None,
        }), 422

    return jsonify({
        "traces": traces,
        "output": output.strip() or None,
    })


# ---------------------------------------------------------------------------

def _run_build(job_id: str, workflow_id: str, safe_name: str,
               script_path: str, wf_output_dir: str) -> None:
    dist_dir = os.path.join(wf_output_dir, "dist")
    work_dir = os.path.join(wf_output_dir, "build")
    spec_dir = wf_output_dir

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--distpath", dist_dir,
        "--workpath", work_dir,
        "--specpath", spec_dir,
        "--name", safe_name,
        script_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        _write_job(wf_output_dir, job_id, {
            "status": "error",
            "error":  "PyInstaller timed out (>5 min)",
            "log":    "The build exceeded the 5-minute limit and was killed.\n"
                      f"Run manually: {sys.executable} -m PyInstaller --onefile {script_path}",
        })
        return
    except Exception as exc:
        _write_job(wf_output_dir, job_id, {
            "status": "error",
            "error":  f"Unexpected error: {exc}",
            "log":    traceback.format_exc(),
        })
        return

    log = result.stderr + result.stdout

    if result.returncode != 0:
        _write_job(wf_output_dir, job_id, {
            "status": "error",
            "error":  f"PyInstaller exited with code {result.returncode}",
            "log":    log,
        })
        return

    exe_path = os.path.join(dist_dir, f"{safe_name}.exe")
    if not os.path.exists(exe_path):
        _write_job(wf_output_dir, job_id, {
            "status": "error",
            "error":  "Build reported success but .exe was not found",
            "log":    log + f"\n\nExpected: {exe_path}",
        })
        return

    _write_job(wf_output_dir, job_id, {
        "status":   "success",
        "log":      log,
        "exe_name": f"{safe_name}.exe",
        "error":    None,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return safe.strip("_") or "workflow"
