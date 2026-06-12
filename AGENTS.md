# AGENTS.md

## Runtime

- **Python 3.9** — use `from __future__ import annotations` and `Optional[X]` from `typing`. The `X | Y` union syntax fails at runtime on 3.9.
- Entry point: `python run.py` → Flask on `http://localhost:5000`
- No test framework, no linter, no CI configured. Verify backend with:
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
  - `builder_bp` — validate / preview / build / run / download
- `data/` and `output/` are created at startup by `app/main.py`; never commit them.
- Flask has **three explicit routes** for the React SPA (in `app/main.py`):
  - `/assets/<path>` → `app/static/dist/assets/` (Vite JS/CSS chunks)
  - `/<filename>` → `app/static/dist/<filename>` only if the file exists (favicon, etc.), otherwise falls through to `spa_index()`
  - `/` → `app/static/dist/index.html`
  - These routes must stay **above** any API blueprints in registration order. Do not collapse them into a single catch-all or the assets will 404.

## Frontend

- **React 19 + Vite 8 + React Flow v11 + shadcn/ui + Tailwind CSS v3.**
- Source lives in `frontend/`. Built output goes to `app/static/dist/` (gitignored).
- `app/static/dist/` **must be built before Flask can serve the app**. After cloning or changing frontend code:
  ```bash
  cd frontend
  npm install   # first time only
  npm run build
  ```
- For HMR during development run both:
  ```bash
  python run.py          # terminal 1 — Flask on :5000
  cd frontend && npm run dev  # terminal 2 — Vite on :5173 (proxies /api/* to :5000)
  ```
- Vite asset paths are root-absolute (`/assets/...`). The three Flask routes above are what make this work. If you change `vite.config.js` `build.outDir`, update `DIST_DIR` in `app/main.py` too.

## Frontend node system

- Every node type has **two exports** in `frontend/src/nodes/{Type}Node.jsx`:
  - **Default export** — React Flow canvas card component (`data.instanceName`, `data.config`)
  - **Named export** `{Type}PropsForm` — controlled form component (`{ config, onChange }`)
- Both are registered in `frontend/src/nodes/index.js`:
  - `nodeTypes` — passed to `<ReactFlow nodeTypes={...}>` 
  - `NODE_META` — contains `label`, `icon`, `inputs`, `outputs`, `defaultConfig()`, `PropsForm`
- Node instance names live in `node.data.instanceName` (React Flow state), persisted as `label` in SQLite. `generateInstanceName()` in `WorkflowContext` auto-assigns unique names with numeric suffixes.
- `deleteKeyCode="Delete"` on `<ReactFlow>` handles node deletion natively. The `onNodesDelete` callback closes the props panel reactively. No DOM focus management needed.

## State management

- All graph state is in `WorkflowContext` (`frontend/src/context/WorkflowContext.jsx`) via `useNodesState` / `useEdgesState` from React Flow.
- Auto-save debounce is 800 ms, implemented with `useRef` + `setTimeout` in `WorkflowContext.saveGraph`.
- `saveGraph` maps React Flow node/edge format → API format. `loadGraph` does the reverse. Both mappings are in `WorkflowContext` — do not duplicate them elsewhere.

## Database

- `data/main.db` — registry of all workflows (id, name, description, timestamps).
- `data/{workflow_id}.db` — per-workflow SQLite with `nodes` and `edges` tables.
- `nodes.label` stores the instance name (e.g. `"Set Variables 2"`), not the type string.
- Node `config` is stored as a JSON string column; `get_workflow_graph()` deserialises it automatically.
- `save_workflow_graph()` does a full replace (DELETE + INSERT) — it is not a merge.

## Backend node system

- Every node: subclass `BaseNode` (`app/nodes/base.py`), set `NODE_TYPE`, implement `validate() -> list[str]` and `to_code(indent) -> str`.
- Register in `NODE_REGISTRY` in `app/codegen/generator.py` — if missing, build raises `ValueError: Unknown node type`.
- `SchedulerNode` is special: `to_code()` emits only the `while True:` header; `loop_close_code()` emits the `time.sleep` at loop bottom. The generator calls both.
- Only **one** Scheduler node per workflow is allowed; the generator enforces this.
- Nodes placed **before** the Scheduler execute outside the loop (setup). Nodes **after** it execute inside the loop.
- `_indent(code, spaces)` prefixes every line — use it in `to_code`, never manual string concat.

## Code generation

- `app/codegen/generator.py` uses `_topological_waves()` (Kahn's BFS) to group independent nodes into execution **waves**.
- Single-node wave: emitted inline. Multi-node wave: wrapped in `ThreadPoolExecutor` with `wait(ALL_COMPLETED)`.
- A cycle raises `ValueError` (surfaced as 422 from the build endpoint).
- Generated scripts are written to `output/{workflow_id}/{safe_name}.py` before PyInstaller runs.

## Build / EXE

- Build is **async**: `POST /api/workflows/{id}/build` returns a `job_id` immediately. Poll `GET .../build/status/{job_id}` every 2 s.
- PyInstaller `--onefile --noconfirm`. Output: `output/{workflow_id}/dist/{safe_name}.exe`.
- `_safe_filename()` replaces non-alphanumeric characters (except `-_`) with `_`.
- Build timeout: 300 s. First build is slow (~1 min) due to PyInstaller analysis.
- `pyinstaller` must be on `PATH`; if missing, the endpoint returns 500 with a pip install hint.

## Adding a new node (checklist)

**Backend (Python):**
1. `app/nodes/{type}.py` — subclass `BaseNode`, set `NODE_TYPE`
2. Register in `NODE_REGISTRY` in `app/codegen/generator.py`

**Frontend (React):**
3. `frontend/src/nodes/{Type}Node.jsx` — default canvas card + named `{Type}PropsForm`
4. Register both in `frontend/src/nodes/index.js` (`nodeTypes` + `NODE_META`)
5. `cd frontend && npm run build`
