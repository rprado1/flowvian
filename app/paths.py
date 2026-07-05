from __future__ import annotations

import os
import sys


APP_NAME_WINDOWS = "WorkflowBuilder"
APP_NAME_UNIX = "workflow-builder"


def _normalize_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _default_app_base_dir() -> str:
    if sys.platform.startswith("win"):
        appdata = os.getenv("APPDATA")
        if appdata:
            return os.path.join(appdata, APP_NAME_WINDOWS)
        return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", APP_NAME_WINDOWS)

    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            APP_NAME_WINDOWS,
        )

    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return os.path.join(_normalize_path(xdg_config_home), APP_NAME_UNIX)
    return os.path.join(os.path.expanduser("~"), ".config", APP_NAME_UNIX)


def get_data_dir() -> str:
    configured = os.getenv("WBUI_DATA_DIR")
    if configured:
        return _normalize_path(configured)
    return os.path.join(_default_app_base_dir(), "data")


def get_output_dir() -> str:
    configured = os.getenv("WBUI_OUTPUT_DIR")
    if configured:
        return _normalize_path(configured)
    return os.path.join(_default_app_base_dir(), "output")
