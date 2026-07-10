#!/usr/bin/env python
"""Build wbui runtime binary for current platform.

Usage:
    python scripts/build-runtime.py

Build this script on each target OS natively:
  - Windows x64 -> wbui-win32-x64.exe
  - Linux x64   -> wbui-linux-x64
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts" / "runtime"
BUILD_DIR = ROOT / "artifacts" / "pyinstaller-build"
SPEC_DIR = ROOT / "artifacts" / "pyinstaller-spec"


def target_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if machine not in {"x86_64", "amd64"}:
        raise RuntimeError(f"Unsupported architecture '{machine}'. Expected x64.")

    if system == "windows":
        return "wbui-win32-x64"
    if system == "linux":
        return "wbui-linux-x64"

    raise RuntimeError(f"Unsupported OS '{system}'. Build only on Windows or Linux.")


def ensure_frontend_dist() -> None:
    dist_index = ROOT / "app" / "static" / "dist" / "index.html"
    if not dist_index.exists():
        raise RuntimeError(
            "Missing app/static/dist/index.html. Build frontend first: "
            "cd frontend && npm install && npm run build"
        )


def run_pyinstaller(binary_stem: str) -> Path:
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(SPEC_DIR, exist_ok=True)

    # PyInstaller uses ';' on Windows and ':' on Unix for --add-data.
    data_sep = ";" if os.name == "nt" else ":"
    static_src = ROOT / "app" / "static"
    add_data = f"{static_src}{data_sep}app/static"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(ARTIFACTS_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--name",
        binary_stem,
        "--add-data",
        add_data,
        str(ROOT / "run.py"),
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    expected = ARTIFACTS_DIR / (binary_stem + (".exe" if os.name == "nt" else ""))
    if not expected.exists():
        raise RuntimeError(f"Build completed but output not found: {expected}")

    if os.name != "nt":
        expected.chmod(0o755)

    return expected


def main() -> int:
    try:
        ensure_frontend_dist()
        binary_stem = target_name()
        output = run_pyinstaller(binary_stem)
    except Exception as exc:
        print(f"[build-runtime] ERROR: {exc}")
        return 1

    print(f"[build-runtime] OK: {output}")
    print("Upload this file to the GitHub release that npm uses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
