from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import traceback
import uuid
import socket

from flask import Blueprint, jsonify, current_app, request, send_file
from app.db.manager import get_workflow_meta, get_workflow_graph
from app.codegen.generator import generate_script, validate_graph, generate_run_script

builder_bp = Blueprint("builder", __name__)

# Maximum wall-clock time for /run workflow execution.
# Increased to support Wait nodes with delays > 30 seconds.
RUN_TIMEOUT_SECONDS = 300
RUN_WEBHOOK_WAIT_SECONDS = 90

_RUN_LOCK = threading.Lock()
_RUN_STATE: dict[str, dict] = {}


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
    errors = validate_graph(graph["nodes"], graph["edges"], require_trigger=True)
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
        script = generate_script(meta["name"], workflow_id, graph["nodes"], graph["edges"])
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

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}
    raw_debug = body.get("debug", False)
    if isinstance(raw_debug, str):
        debug = raw_debug.strip().lower() in {"1", "true", "yes", "on"}
    else:
        debug = bool(raw_debug)

    try:
        script = generate_script(meta["name"], workflow_id, graph["nodes"], graph["edges"], debug=debug)
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
            job_file, script_path, safe_name, dist_dir, work_dir, spec_dir, workflow_id,
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

    webhook_nodes = [n for n in graph.get("nodes", []) if str(n.get("type") or "") == "webhook"]
    if webhook_nodes:
        webhook_config = webhook_nodes[0].get("config") if isinstance(webhook_nodes[0].get("config"), dict) else {}
        raw_port = webhook_config.get("port", 8000)
        raw_host = str(webhook_config.get("host", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1"
        try:
            webhook_port = int(raw_port)
        except Exception:
            webhook_port = 8000

        if webhook_port > 0:
            host_candidates = ["127.0.0.1"]
            if raw_host not in host_candidates:
                host_candidates.append(raw_host)
            port_busy = any(_is_port_open(h, webhook_port) for h in host_candidates)
            if port_busy:
                return jsonify({
                    "error": (
                        f"Webhook port {webhook_port} is already in use. "
                        "Stop the existing listener/process or change webhook port in node config."
                    ),
                    "phase": "webhook_port_in_use",
                    "port": webhook_port,
                    "host": raw_host,
                }), 409

    try:
        script = generate_run_script(meta["name"], workflow_id, graph["nodes"], graph["edges"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    wf_output_dir = os.path.join(output_dir(), workflow_id)
    os.makedirs(wf_output_dir, exist_ok=True)

    run_script_path = os.path.join(wf_output_dir, "_run.py")
    trace_path = os.path.join(wf_output_dir, "_trace.json")
    final_output_path = os.path.join(wf_output_dir, "_final_output.json")
    stop_path = os.path.join(wf_output_dir, "_stop.json")
    state_path = os.path.join(wf_output_dir, "_run_state.json")

    if os.path.exists(trace_path):
        try:
            os.remove(trace_path)
        except OSError:
            pass

    if os.path.exists(final_output_path):
        try:
            os.remove(final_output_path)
        except OSError:
            pass

    if os.path.exists(stop_path):
        try:
            os.remove(stop_path)
        except OSError:
            pass

    if os.path.exists(state_path):
        try:
            os.remove(state_path)
        except OSError:
            pass

    with open(run_script_path, "w", encoding="utf-8") as f:
        f.write(script)

    env = os.environ.copy()
    env["WORKFLOW_TRACE_PATH"] = trace_path
    env["WORKFLOW_FINAL_OUTPUT_PATH"] = final_output_path
    env["WORKFLOW_WEBHOOK_WAIT_SECONDS"] = str(RUN_WEBHOOK_WAIT_SECONDS)
    env["WORKFLOW_STOP_PATH"] = stop_path
    env["WORKFLOW_RUN_STATE_PATH"] = state_path

    run_started_at = time.perf_counter()
    run_started_at_epoch = time.time()

    try:
        with _RUN_LOCK:
            if workflow_id in _RUN_STATE:
                return jsonify({"error": "A run is already in progress for this workflow"}), 409

        proc = subprocess.Popen(
            [sys.executable, run_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        with _RUN_LOCK:
            _RUN_STATE[workflow_id] = {
                "process": proc,
                "stop_path": stop_path,
            }

        stdout, stderr = proc.communicate(timeout=RUN_TIMEOUT_SECONDS)
        result = subprocess.CompletedProcess(
            args=[sys.executable, run_script_path],
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired:
        return jsonify({
            "error": f"Workflow execution timed out ({RUN_TIMEOUT_SECONDS}s)",
            "traces": [],
            "output": "",
        }), 500
    except Exception as exc:
        return jsonify({
            "error": f"Failed to execute workflow: {exc}",
            "traces": [],
            "output": "",
        }), 500
    finally:
        with _RUN_LOCK:
            _RUN_STATE.pop(workflow_id, None)

    run_elapsed_seconds = round(max(time.perf_counter() - run_started_at, 0.0), 3)

    traces = []
    if os.path.exists(trace_path):
        try:
            with open(trace_path, "r", encoding="utf-8") as f:
                traces = json.load(f)
        except Exception:
            pass

    final_output = None
    if os.path.exists(final_output_path):
        try:
            with open(final_output_path, "r", encoding="utf-8") as f:
                final_output = json.load(f)
        except Exception:
            final_output = None

    if isinstance(final_output, dict):
        final_output["elapsed_seconds"] = run_elapsed_seconds

        branch_elapsed_seconds = {}
        terminals = final_output.get("terminals")
        if isinstance(terminals, list):
            for terminal in terminals:
                if not isinstance(terminal, dict):
                    continue
                terminal_id = str(terminal.get("id", "")).strip()
                if not terminal_id:
                    continue

                terminal_ts = None
                for tr in reversed(traces):
                    if not isinstance(tr, dict):
                        continue
                    if str(tr.get("id", "")).strip() != terminal_id:
                        continue
                    raw_ts = tr.get("ts")
                    if isinstance(raw_ts, (int, float)):
                        terminal_ts = float(raw_ts)
                    break

                if terminal_ts is None:
                    branch_elapsed_seconds[terminal_id] = None
                    continue

                branch_elapsed_seconds[terminal_id] = round(max(terminal_ts - run_started_at_epoch, 0.0), 3)

        final_output["branch_elapsed_seconds"] = branch_elapsed_seconds

        try:
            with open(final_output_path, "w", encoding="utf-8") as f:
                json.dump(final_output, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    output = result.stderr + result.stdout
    if isinstance(final_output, dict):
        final_output_text = json.dumps(final_output, ensure_ascii=False)
        if result.stderr and result.stderr.strip():
            output = result.stderr.strip() + "\n" + final_output_text
        else:
            output = final_output_text

    if result.returncode != 0:
        return jsonify({
            "error": f"Script exited with code {result.returncode}",
            "traces": traces,
            "output": output.strip() or None,
            "final_output": final_output,
        }), 422

    return jsonify({
        "traces": traces,
        "output": output.strip() or None,
        "final_output": final_output,
    })


@builder_bp.route("/<workflow_id>/run/stop", methods=["POST"])
def stop_run_workflow(workflow_id):
    with _RUN_LOCK:
        state = _RUN_STATE.get(workflow_id)

    if not state:
        return jsonify({"stopped": False, "message": "No run in progress"})

    stop_path = state.get("stop_path")
    if stop_path:
        try:
            with open(stop_path, "w", encoding="utf-8") as f:
                json.dump({"stop": True}, f)
        except Exception:
            pass

    return jsonify({
        "stopped": True,
        "message": "Stop requested. Waiting for current run to finish gracefully.",
    })


@builder_bp.route("/<workflow_id>/run/state", methods=["GET"])
def run_state_workflow(workflow_id):
    wf_output_dir = os.path.join(output_dir(), workflow_id)
    state_path = os.path.join(wf_output_dir, "_run_state.json")
    trace_path = os.path.join(wf_output_dir, "_trace.json")
    final_output_path = os.path.join(wf_output_dir, "_final_output.json")

    active_run = False
    with _RUN_LOCK:
        state_entry = _RUN_STATE.get(workflow_id)
        if state_entry is not None:
            proc = state_entry.get("process")
            if proc is not None and proc.poll() is None:
                active_run = True
            else:
                _RUN_STATE.pop(workflow_id, None)

    has_result = os.path.exists(trace_path) or os.path.exists(final_output_path)

    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict):
                status = str(state.get("status") or "").strip().lower()
                phase = str(state.get("phase") or "").strip().lower()
                if status == "running" and not active_run:
                    if has_result:
                        return jsonify({"status": "completed", "phase": "done", "inferred": True})
                    return jsonify({"status": "idle", "inferred": True})
                if status == "running" and phase == "waiting_webhook":
                    listen_host = str(state.get("listen_host") or "").strip() or "0.0.0.0"
                    host = str(state.get("host") or "").strip() or "127.0.0.1"
                    raw_port = state.get("port", 0)
                    try:
                        port = int(raw_port)
                    except Exception:
                        port = 0
                    port_open = port > 0 and (_is_port_open("127.0.0.1", port) or _is_port_open(host, port))
                    state["listener_alive"] = bool(port_open)
                    if not port_open and not has_result:
                        return jsonify({
                            "status": "error",
                            "phase": "webhook_listener_unavailable",
                            "error": "Webhook listener is not reachable on configured port",
                            "host": host,
                            "listen_host": listen_host,
                            "port": port,
                        })
                return jsonify(state)
        except Exception:
            pass

    if active_run:
        return jsonify({"status": "running", "phase": "starting"})

    if has_result:
        return jsonify({"status": "completed", "phase": "done", "inferred": True})

    return jsonify({"status": "idle"})


@builder_bp.route("/<workflow_id>/run/result", methods=["GET"])
def run_result_workflow(workflow_id):
    meta = get_workflow_meta(data_dir(), workflow_id)
    if not meta:
        return jsonify({"error": "not found"}), 404

    wf_output_dir = os.path.join(output_dir(), workflow_id)
    trace_path = os.path.join(wf_output_dir, "_trace.json")
    final_output_path = os.path.join(wf_output_dir, "_final_output.json")

    if not os.path.exists(trace_path) and not os.path.exists(final_output_path):
        return jsonify({"error": "run result not available"}), 404

    traces = []
    final_output = None

    if os.path.exists(trace_path):
        try:
            with open(trace_path, "r", encoding="utf-8") as f:
                loaded_traces = json.load(f)
            if isinstance(loaded_traces, list):
                traces = loaded_traces
        except Exception:
            traces = []

    if os.path.exists(final_output_path):
        try:
            with open(final_output_path, "r", encoding="utf-8") as f:
                final_output = json.load(f)
        except Exception:
            final_output = None

    output = None
    if isinstance(final_output, dict):
        output = json.dumps(final_output, ensure_ascii=False)

    return jsonify({
        "traces": traces,
        "output": output,
        "final_output": final_output,
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


def _is_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False
