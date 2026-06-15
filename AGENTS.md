# AGENTS.md

Repository guide for coding agents working in `workflow-exe`.

## Rules Discovery

- Checked for Cursor rules in `.cursor/rules/` and `.cursorrules`: **none found**.
- Checked for Copilot instructions in `.github/copilot-instructions.md`: **none found**.
- This file is the primary agent guidance for this repo.

## Runtime + Stack

- Backend: **Python 3.9**, Flask 3.1, SQLite.
- Frontend: **React 19**, Vite 8, React Flow v11, Tailwind v3, shadcn/ui.
- Build packaging: PyInstaller `--onefile`.
- App entrypoint: `python run.py` (run from repo root).

## Build / Lint / Test Commands

### Backend

- Install deps:
  ```bash
  pip install -r requirements.txt
  ```
- Sanity import check:
  ```bash
  python -c "from app.main import app; print('OK')"
  ```
- Byte-compile key modules (quick syntax check):
  ```bash
  python -m py_compile app/main.py app/codegen/generator.py app/api/builder.py
  ```

### Frontend

- Install deps:
  ```bash
  cd frontend && npm install
  ```
- Dev server:
  ```bash
  cd frontend && npm run dev
  ```
- Build:
  ```bash
  cd frontend && npm run build
  ```
- Lint all frontend:
  ```bash
  cd frontend && npm run lint
  ```
- Lint a single file:
  ```bash
  cd frontend && npm run lint -- src/components/Canvas.jsx
  ```

### Tests (current state)

- No pytest/unittest suite is configured.
- Use API smoke tests with Flask test client.
- Single-test equivalent (one endpoint):
  ```bash
  python -c "from app.main import app; c=app.test_client(); r=c.post('/api/workflows/', json={'name':'smoke'}); print(r.status_code, r.is_json)"
  ```
- Single workflow validation smoke:
  ```bash
  python -c "from app.codegen.generator import validate_graph; print(validate_graph([{'id':'n1','type':'set_variables','config':{'variables':[{'key':'x','value':'1'}]}}], []))"
  ```

## Local Development Workflow

- Terminal 1 (backend): `python run.py`
- Terminal 2 (frontend): `cd frontend && npm run dev`
- Production-like local run requires frontend build in `app/static/dist/`.

## Architecture Constraints

- `app/main.py` sets `DATA_DIR` and `OUTPUT_DIR` in `app.config`; use these everywhere.
- Never hardcode `data/` or `output/` paths in request handlers.
- Two blueprints share `/api/workflows`:
  - `workflows_bp`: CRUD + graph persistence
  - `builder_bp`: validate / preview / build / run / download
- SPA serving in `app/main.py` uses explicit routes (`/assets/*`, `/<filename>`, `/`). Keep order intact.

## Frontend Node System

- Each node file `frontend/src/nodes/{Type}Node.jsx` exports:
  - default canvas component
  - named `{Type}PropsForm`
- Register both in `frontend/src/nodes/index.js`:
  - `nodeTypes`
  - `NODE_META` with `defaultConfig`, labels, io counts, `PropsForm`
- Graph state is centralized in `WorkflowContext`.
- Do not duplicate node/edge mapping logic outside `WorkflowContext`.

## Code Style Guidelines

### Python

- Use Python 3.9-compatible typing.
- Prefer:
  - `from __future__ import annotations`
  - `Optional[T]` and `typing` generics
- Avoid `X | Y` union syntax (not safe in this runtime).
- Keep imports at module top. Do **not** emit function-local imports unless absolutely required.
- Use explicit, descriptive names (`workflow_id`, `branch_count`, `incoming_count`).
- Favor small helper functions over long inline blocks.
- Error handling:
  - validate early, return clear user-facing messages
  - raise `ValueError` for invalid graph/codegen states
  - preserve actionable context in error text
- In generated code, keep deterministic ordering where possible.

### JavaScript / React

- Follow existing project style (semi-colons, single quotes, functional components).
- Use hooks idiomatically (`useCallback`, `useEffect`, `useRef`) and stable deps.
- Keep node props forms controlled (`config`, `onChange`).
- Prefer immutable updates for nodes/edges.
- Keep React Flow handles explicit and predictable (`input_1`, `output_1`, `in-0`, etc.).
- Avoid hidden side effects in render paths.

### Formatting / Lint

- Frontend lint config is in `frontend/eslint.config.js`.
- No backend formatter/linter configured; match existing code style closely.
- Keep diffs minimal and focused on task intent.

## Naming Conventions

- Node type ids: snake_case (e.g., `get_current_date_utc`, `add_time_to_date`, `merge`).
- React node component files: PascalCase + `Node.jsx`.
- Props form export: `{Type}PropsForm`.
- Backend node class names: PascalCase + `Node` suffix.

## Data + Persistence

- `data/main.db`: workflow registry.
- `data/{workflow_id}.db`: per-workflow `nodes` + `edges`.
- `save_workflow_graph()` is full replace (DELETE + INSERT), not patch merge.
- `nodes.label` stores instance name, not node type.

## Build / EXE Notes

- Build endpoint is async and returns `job_id`.
- Output exe path: `output/{workflow_id}/dist/{safe_name}.exe`.
- First build can be slow due to PyInstaller analysis.
- Do not commit generated `data/`, `output/`, or `app/static/dist/` artifacts.

## Adding a New Node Checklist

1. Add backend node class in `app/nodes/{type}.py`.
2. Register class in `NODE_REGISTRY` (`app/codegen/generator.py`).
3. Add frontend node component + props form in `frontend/src/nodes/{Type}Node.jsx`.
4. Register in `frontend/src/nodes/index.js` (`nodeTypes` + `NODE_META`).
5. Run `cd frontend && npm run build`.
6. Run backend sanity import and a smoke API call.

## Agent Behavior Expectations

- Prefer small, verifiable changes.
- After changes, run the narrowest relevant checks first, then broader checks.
- If introducing behavior changes, update `README.md` and planning docs under `_docs/planning/`.
