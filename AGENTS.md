# AGENTS.md

Repository guide for coding agents working in `workflow-exe`.

## Rules Discovery

- Cursor rules in `.cursor/rules/`: **none found**.
- Root `.cursorrules`: **none found**.
- Copilot instructions in `.github/copilot-instructions.md`: **none found**.
- This file is the canonical agent instruction set for this repository.

## Project Snapshot

- Backend: Python 3.9, Flask 3.1, SQLite.
- Frontend: React 19, Vite 8, React Flow v11, Tailwind v3, shadcn/ui.
- Packaging: PyInstaller one-file executable build.
- Entrypoint: `python run.py` from repository root.
- Platform assumptions: development is primarily Windows.

## Build, Lint, and Test Commands

### Backend Commands

- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Run backend server:
  ```bash
  python run.py
  ```
- Import sanity check (fast fail for broken imports):
  ```bash
  python -c "from app.main import app; print('OK')"
  ```
- Syntax check key modules:
  ```bash
  python -m py_compile app/main.py app/codegen/generator.py app/api/builder.py
  ```

### Frontend Commands

- Install dependencies:
  ```bash
  cd frontend && npm install
  ```
- Start Vite dev server:
  ```bash
  cd frontend && npm run dev
  ```
- Production build (required for Flask-served UI):
  ```bash
  cd frontend && npm run build
  ```
- Lint full frontend:
  ```bash
  cd frontend && npm run lint
  ```
- Lint one file:
  ```bash
  cd frontend && npm run lint -- src/components/Canvas.jsx
  ```

### Test Status and Single-Test Equivalents

- No formal `pytest` or frontend test runner is configured.
- Use targeted smoke checks as the “single test” workflow.
- Single endpoint smoke test:
  ```bash
  python -c "from app.main import app; c=app.test_client(); r=c.post('/api/workflows/', json={'name':'smoke'}); print(r.status_code, r.is_json)"
  ```
- Single graph-validation smoke test:
  ```bash
  python -c "from app.codegen.generator import validate_graph; print(validate_graph([{'id':'n1','type':'set_variables','config':{'variables':[{'key':'x','value':'1'}]}}], []))"
  ```

## Local Development Workflow

- Terminal 1: `python run.py` (Flask on `:5000`).
- Terminal 2: `cd frontend && npm run dev` (Vite on `:5173`).
- For production-like behavior, build frontend into `app/static/dist/`.
- Keep venv active and run all commands from repo root unless noted.

## Architecture Guardrails

- `app/main.py` defines `DATA_DIR` and `OUTPUT_DIR` in Flask config; use those values.
- Do not hardcode `data/` or `output/` paths in handlers or node code.
- API routing is split across two blueprints on `/api/workflows`:
  - `workflows_bp`: workflow CRUD and graph persistence.
  - `builder_bp`: validate, preview, run, build, download.
- SPA serving route order in `app/main.py` is intentional (`/assets/*`, `/<filename>`, `/`).
- Preserve branch isolation and terminal-branch output contract in codegen logic.

## Frontend Node System Contract

- Each node file in `frontend/src/nodes/` must export:
  - default visual node component.
  - named props form: `{Type}PropsForm`.
- Register node in `frontend/src/nodes/index.js` in both:
  - `nodeTypes` map.
  - `NODE_META` entry with label/icon/description/io/defaultConfig/PropsForm.
- Keep node forms controlled via `config` and `onChange`.
- Keep graph mapping/state logic centralized in `WorkflowContext`.

## Code Style Guidelines

### Python

- Target Python 3.9 compatibility for syntax and typing.
- Prefer `from __future__ import annotations` in new backend modules.
- Use `typing.Optional`, `typing.Dict`, `typing.List` style compatibility when needed.
- Avoid PEP 604 unions (`X | Y`) for runtime compatibility.
- Keep imports at module top; avoid function-local imports unless unavoidable.
- Keep functions small; extract helpers for parsing, validation, and transformation.
- Use descriptive names (`workflow_id`, `incoming_count`, `branch_count`).
- Validation style:
  - validate early and return actionable messages.
  - use `ValueError` for invalid graph/codegen states.
  - include node type/label context in errors when possible.
- Generated-code output should be deterministic where practical.

### JavaScript / React

- Follow existing repo style: functional components, semicolons, single quotes.
- Use hooks idiomatically and include stable dependency arrays.
- Prefer immutable updates for objects/arrays and graph entities.
- Avoid side effects during render.
- Keep React Flow handles explicit and predictable (`input_1`, `output_1`, etc.).
- Keep props forms simple, controlled, and schema-like.

### Formatting and Linting

- Frontend lint config: `frontend/eslint.config.js`.
- No backend formatter/linter is configured; mirror existing style carefully.
- Keep diffs focused; avoid broad opportunistic refactors.

## Naming Conventions

- Node type IDs: snake_case (example: `telegram_send_message`).
- Backend node classes: PascalCase + `Node` suffix.
- React node files: PascalCase + `Node.jsx`.
- Props form export: `{Type}PropsForm`.
- Config keys: snake_case in backend and frontend node config.

## Data, Persistence, and Secrets

- Workflow registry: `data/main.db`.
- Per-workflow graph DB: `data/{workflow_id}.db`.
- Node config is stored as JSON in `nodes.config`.
- Graph saves are full replace (`DELETE` + `INSERT`), not partial patch.
- `nodes.label` stores instance name, not node type.
- Secret handling is special-cased for `set_variables`; preserve masking/encryption flow.

## Build and Artifact Notes

- Build endpoint is asynchronous and returns a `job_id`.
- EXE output path: `output/{workflow_id}/dist/{safe_name}.exe`.
- First build is often slow due to PyInstaller analysis.
- Never commit generated artifacts under `data/`, `output/`, or `app/static/dist/`.

## Change Checklist for Agents

1. Make the smallest viable change.
2. Run the narrowest relevant check first (single-file lint, smoke command).
3. Run broader checks only after targeted checks pass.
4. For new nodes, update backend class, registry, frontend component, and `NODE_META`.
5. If behavior changes, update `README.md` and relevant docs under `_docs/planning/`.
6. Preserve API/output contracts unless change request explicitly allows breaking changes.
