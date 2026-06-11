# AGENTS.md

## Runtime

- **Python 3.9** — use `from __future__ import annotations` and `Optional[X]` from `typing`. The `X | Y` union syntax fails at runtime on 3.9.
- Entry point: `python run.py` → Flask on `http://localhost:5000`
- No test framework, no linter, no CI configured. Verify with:
  ```bash
  python -c "from app.main import app; print('OK')"
  ```
- Quick API smoke-test via Flask test client (no server needed):
  ```python
  from app.main import app
  client = app.test_client()
  r = client.post('/api/workflows/', json={'name': 'test'})
  ```

## Architecture

- `run.py` imports `app.main.app` — always run from the repo root so package imports resolve.
- `app/main.py` sets `DATA_DIR` and `OUTPUT_DIR` on `app.config`; all DB and build code reads these via `current_app.config`. Do not hardcode paths.
- Two Flask blueprints share the same URL prefix `/api/workflows`:
  - `workflows_bp` — CRUD + graph save/load
  - `builder_bp` — validate / preview / build / download
- `data/` and `output/` are created at startup by `app/main.py`; never commit them.

## Database

- `data/main.db` — registry of all workflows (id, name, description, timestamps).
- `data/{workflow_id}.db` — per-workflow SQLite with `nodes` and `edges` tables.
- Node `config` is stored as a JSON string column; `get_workflow_graph()` deserialises it automatically.
- `save_workflow_graph()` does a full replace (DELETE + INSERT) — it is not a merge.

## Node system

- Every node: subclass `BaseNode` (`app/nodes/base.py`), set `NODE_TYPE`, implement `validate() -> list[str]` and `to_code(indent) -> str`.
- Register in `NODE_REGISTRY` in `app/codegen/generator.py` — if missing, build raises `ValueError: Unknown node type`.
- `SchedulerNode` is special: `to_code()` emits only the `while True:` header; `loop_close_code()` emits the `time.sleep` at loop bottom. The generator calls both.
- Only **one** Scheduler node per workflow is allowed; the generator enforces this.
- Nodes placed **before** the Scheduler in the graph execute outside the loop (setup code). Nodes **after** it execute inside the loop.
- `_indent(code, spaces)` prefixes every line — use it in `to_code`, never manual string concat.

## Code generation

- `app/codegen/generator.py` runs Kahn's BFS topological sort on the graph DAG.
- A cycle raises `ValueError` (surfaced as a 422 from the build endpoint).
- Generated scripts are written to `output/{workflow_id}/{safe_name}.py` before PyInstaller runs.

## Build / EXE

- Build endpoint: `POST /api/workflows/{id}/build`
- PyInstaller is invoked via `subprocess.run` with `--onefile --noconfirm`. Output lands in `output/{workflow_id}/dist/{safe_name}.exe`.
- `_safe_filename()` replaces non-alphanumeric characters (except `-_`) with `_`. Workflow name → EXE filename follows this rule.
- Build timeout is 300 s. First build is slow (~1 min) due to PyInstaller analysis.
- `pyinstaller` must be on `PATH`; if missing, the endpoint returns a 500 with a pip install hint.

## Frontend

- Single-page app in `app/static/index.html` (Vanilla JS + Drawflow 0.0.59, vendored locally).
- Node JS definitions live in `app/static/js/nodes/{type}.js`. Each exports a plain object with: `type`, `html()`, `defaultConfig()`, `renderProps()`, `readProps()`, `updateNodePreview()`, and optional `afterRender()`.
- `app/static/js/app.js` stores per-node configs in `nodeConfigs` (keyed by Drawflow's internal integer id, **not** the server-side UUID). On save, it maps Drawflow ids back to the graph payload.
- Auto-save fires 800 ms after any graph change. Manual save button also available.
- Drawflow internal node ids are integers and differ from the `id` stored in SQLite — never conflate them.

## Adding a new node (checklist)

1. `app/nodes/{type}.py` — subclass `BaseNode`, set `NODE_TYPE`
2. Register in `NODE_REGISTRY` in `app/codegen/generator.py`
3. `app/static/js/nodes/{type}.js` — define the JS object (see existing nodes for shape)
4. Add `<script>` tag in `app/static/index.html` before `app.js`
5. Add palette entry (`<div class="palette-node" data-type="{type}">`) in `index.html`
