from __future__ import annotations
import sqlite3
import os
import uuid
from datetime import datetime
from typing import Optional


def get_main_db_path(data_dir: str) -> str:
    return os.path.join(data_dir, "main.db")


def get_workflow_db_path(data_dir: str, workflow_id: str) -> str:
    return os.path.join(data_dir, f"{workflow_id}.db")


# ---------------------------------------------------------------------------
# Main DB — registry of all workflows
# ---------------------------------------------------------------------------

def init_main_db(data_dir: str) -> None:
    """Create main.db and the workflows table if they don't exist."""
    conn = sqlite3.connect(get_main_db_path(data_dir))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def list_workflows(data_dir: str) -> list[dict]:
    init_main_db(data_dir)
    conn = sqlite3.connect(get_main_db_path(data_dir))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, description, created_at, updated_at FROM workflows ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_workflow_meta(data_dir: str, workflow_id: str) -> Optional[dict]:
    init_main_db(data_dir)
    conn = sqlite3.connect(get_main_db_path(data_dir))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, name, description, created_at, updated_at FROM workflows WHERE id = ?",
        (workflow_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_workflow(data_dir: str, name: str, description: str = "") -> dict:
    init_main_db(data_dir)
    workflow_id = uuid.uuid4().hex
    now = datetime.utcnow().isoformat()

    # Register in main.db
    conn = sqlite3.connect(get_main_db_path(data_dir))
    conn.execute(
        "INSERT INTO workflows (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (workflow_id, name, description, now, now)
    )
    conn.commit()
    conn.close()

    # Create per-workflow SQLite
    _init_workflow_db(data_dir, workflow_id)

    return {"id": workflow_id, "name": name, "description": description, "created_at": now, "updated_at": now}


def update_workflow_meta(data_dir: str, workflow_id: str, name: str, description: str) -> Optional[dict]:
    init_main_db(data_dir)
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(get_main_db_path(data_dir))
    conn.execute(
        "UPDATE workflows SET name = ?, description = ?, updated_at = ? WHERE id = ?",
        (name, description, now, workflow_id)
    )
    conn.commit()
    conn.close()
    return get_workflow_meta(data_dir, workflow_id)


def delete_workflow(data_dir: str, workflow_id: str) -> bool:
    init_main_db(data_dir)
    conn = sqlite3.connect(get_main_db_path(data_dir))
    cur = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    conn.commit()
    conn.close()

    # Remove per-workflow DB file
    db_path = get_workflow_db_path(data_dir, workflow_id)
    if os.path.exists(db_path):
        os.remove(db_path)

    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Per-workflow DB — nodes and edges
# ---------------------------------------------------------------------------

def _init_workflow_db(data_dir: str, workflow_id: str) -> None:
    """Create the per-workflow SQLite with nodes and edges tables."""
    conn = sqlite3.connect(get_workflow_db_path(data_dir, workflow_id))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id       TEXT PRIMARY KEY,
            type     TEXT NOT NULL,
            label    TEXT NOT NULL,
            pos_x    REAL NOT NULL DEFAULT 0,
            pos_y    REAL NOT NULL DEFAULT 0,
            config   TEXT NOT NULL DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id              TEXT PRIMARY KEY,
            source_node_id  TEXT NOT NULL,
            target_node_id  TEXT NOT NULL,
            source_output   TEXT NOT NULL DEFAULT 'output_1',
            target_input    TEXT NOT NULL DEFAULT 'input_1'
        )
    """)
    conn.commit()
    conn.close()


def get_workflow_conn(data_dir: str, workflow_id: str) -> sqlite3.Connection:
    """Return a connection to the per-workflow DB (caller must close)."""
    db_path = get_workflow_db_path(data_dir, workflow_id)
    if not os.path.exists(db_path):
        _init_workflow_db(data_dir, workflow_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_workflow_graph(data_dir: str, workflow_id: str) -> dict:
    """Return nodes and edges for a workflow."""
    conn = get_workflow_conn(data_dir, workflow_id)
    nodes = [dict(r) for r in conn.execute("SELECT * FROM nodes").fetchall()]
    edges = [dict(r) for r in conn.execute("SELECT * FROM edges").fetchall()]
    conn.close()

    # Parse config JSON
    import json
    for node in nodes:
        try:
            node["config"] = json.loads(node["config"])
        except Exception:
            node["config"] = {}

    return {"nodes": nodes, "edges": edges}


def save_workflow_graph(data_dir: str, workflow_id: str, nodes: list, edges: list) -> None:
    """Replace all nodes and edges for a workflow atomically."""
    import json
    conn = get_workflow_conn(data_dir, workflow_id)
    conn.execute("DELETE FROM nodes")
    conn.execute("DELETE FROM edges")

    for node in nodes:
        conn.execute(
            "INSERT INTO nodes (id, type, label, pos_x, pos_y, config) VALUES (?, ?, ?, ?, ?, ?)",
            (
                node["id"],
                node["type"],
                node.get("label", node["type"]),
                node.get("pos_x", 0),
                node.get("pos_y", 0),
                json.dumps(node.get("config", {}))
            )
        )

    for edge in edges:
        conn.execute(
            "INSERT INTO edges (id, source_node_id, target_node_id, source_output, target_input) VALUES (?, ?, ?, ?, ?)",
            (
                edge["id"],
                edge["source_node_id"],
                edge["target_node_id"],
                edge.get("source_output", "output_1"),
                edge.get("target_input", "input_1")
            )
        )

    conn.commit()

    # Update updated_at in main.db
    now = datetime.utcnow().isoformat()
    main_conn = sqlite3.connect(get_main_db_path(data_dir))
    main_conn.execute("UPDATE workflows SET updated_at = ? WHERE id = ?", (now, workflow_id))
    main_conn.commit()
    main_conn.close()

    conn.close()
