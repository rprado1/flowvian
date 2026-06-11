"""
Standalone build worker — runs as a separate process, completely independent
of the Flask server and its reloader.

Usage:
    python -m app.build_worker <job_file> <script_path> <safe_name>
                               <dist_dir> <work_dir> <spec_dir>

Writes the final job state to <job_file> when done.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback


def _write(job_file: str, payload: dict) -> None:
    tmp = job_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, job_file)


def main() -> None:
    _, job_file, script_path, safe_name, dist_dir, work_dir, spec_dir = sys.argv

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
        _write(job_file, {
            "status": "error",
            "error":  "PyInstaller timed out (>5 min)",
            "log":    f"Run manually: {sys.executable} -m PyInstaller --onefile {script_path}",
        })
        return
    except Exception as exc:
        _write(job_file, {
            "status": "error",
            "error":  f"Unexpected error: {exc}",
            "log":    traceback.format_exc(),
        })
        return

    log = result.stderr + result.stdout

    if result.returncode != 0:
        _write(job_file, {
            "status": "error",
            "error":  f"PyInstaller exited with code {result.returncode}",
            "log":    log,
        })
        return

    exe_path = os.path.join(dist_dir, f"{safe_name}.exe")
    if not os.path.exists(exe_path):
        _write(job_file, {
            "status": "error",
            "error":  "Build reported success but .exe was not found",
            "log":    log + f"\n\nExpected: {exe_path}",
        })
        return

    _write(job_file, {
        "status":   "success",
        "log":      log,
        "exe_name": f"{safe_name}.exe",
        "error":    None,
    })


if __name__ == "__main__":
    main()
