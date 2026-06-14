# WorkflowEXE Builder

Visual tool for creating workflows and compiling them as Windows `.exe` executables.

Design the flow by dragging nodes onto an n8n-style canvas, configure each step, and generate a standalone `.exe` with one click.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, Flask 3.1, SQLite |
| Frontend | React 19, Vite 8, React Flow v11 |
| UI components | shadcn/ui + Tailwind CSS v3 |
| Code generation | PyInstaller 6 (`--onefile`) |

---

## Requirements

- **Python 3.9+**
- **Node.js 18+** and npm (required to rebuild the frontend)
- **Windows** — the generated `.exe` is Windows-only

---

## Installation

**1. Clone the repository and enter the directory:**

```bash
git clone <repo-url>
cd workflow-exe
```

**2. Create and activate the Python virtual environment:**

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat
```

**3. Install Python dependencies:**

```bash
pip install -r requirements.txt
```

---

## Running the app

**1. Build the React frontend (required after cloning — `dist/` is not committed):**

```bash
cd frontend
npm install
npm run build
cd ..
```

**2. Start Flask:**

```bash
python run.py
```

Open `http://localhost:5000` in your browser.

> Always run from the project root with the venv active.

---

## Frontend development

To work on the React source with hot module replacement:

**1. Install Node dependencies (first time only):**

```bash
cd frontend
npm install
```

**2. Start Vite dev server and Flask simultaneously:**

```bash
# Terminal 1 — backend
python run.py

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api/*` requests to Flask on `:5000`.

**3. Build for production (required for Flask to serve the app at `:5000`):**

```bash
cd frontend
npm run build
```

This writes the bundle to `app/static/dist/`. Flask serves the assets via dedicated routes:

- `/` → `dist/index.html`
- `/assets/*` → `dist/assets/` (JS and CSS chunks)
- Other root-level files → served from `dist/` if they exist

---

## Interface

### Top bar

| Element | Description |
|---|---|
| Workflow name | Click to rename |
| **Preview Code** | Shows the generated Python code |
| **Save** | Saves the graph manually (auto-save also runs 800 ms after any change) |
| **▶ Run** | Executes the workflow and displays per-node input/output in the results panel |
| **⚙ Generate EXE** | Compiles the workflow to a standalone `.exe` via PyInstaller |

### Left sidebar

- **Workflow list** — create, select, delete
- **Node palette** — drag nodes onto the canvas

### Right panel

Opens when clicking a node. Shows the configuration form for that node. Close with `×` or press **Delete** to remove the selected node.

### Run results panel

Appears after clicking **▶ Run**. Displays:

- A per-node execution table (`items_in` / `items_out` and status)
- **Final Output (by terminal branch)**, where each terminal branch is returned separately

---

## Available nodes

### ⏱ Scheduler

Runs the workflow in a loop with a configurable pause between iterations. Only one Scheduler per workflow is allowed.

| Field | Type | Description |
|---|---|---|
| Interval | number | Pause between iterations |
| Unit | seconds / minutes / hours | Interval unit |

```python
_sleep_seconds = 60.0
while True:
    # rest of the workflow
    time.sleep(_sleep_seconds)
```

### 📦 Set Variables

Assigns key=value pairs to the workflow context.

| Field | Description |
|---|---|
| key | Valid Python variable name |
| value | Value (stored as string) |

```python
my_variable = 'value'
```

### 📅 Get Current Date UTC

Captures the current UTC date/time into a variable.

| Field | Description |
|---|---|
| Output variable name | Name of the result variable |

```python
current_date_utc = datetime.now(timezone.utc)
```

### ⏩ Add Time to Date

Adds days, hours, minutes, and/or seconds to an existing datetime variable.

| Field | Description |
|---|---|
| Input datetime variable | Variable holding the source datetime |
| Days / Hours / Minutes / Seconds | Amount to add |
| Output variable name | Name of the result variable |

```python
new_date = source_date + timedelta(days=1, hours=2)
```

### ⏪ Subtract Time from Date

Subtracts days, hours, minutes, and/or seconds from an existing datetime variable.

| Field | Description |
|---|---|
| Input datetime variable | Variable holding the source datetime |
| Days / Hours / Minutes / Seconds | Amount to subtract |
| Output variable name | Name of the result variable |

```python
new_date = source_date - timedelta(minutes=30)
```

### ⬡ Merge

Combines multiple incoming branches explicitly using strategy `append`.

| Field | Description |
|---|---|
| Strategy | Fixed to `append` |
| Branches to combine | Number of incoming handles required (`branch_count`, minimum 2) |

Notes:

- Only `merge` nodes can have multiple incoming edges.
- Each incoming handle (`in-0`, `in-1`, ...) accepts a single connection.
- Validation fails if incoming connections do not match `branch_count`.

---

## Node naming

When a node is added to the canvas, it receives a unique name automatically:

- First instance: `Set Variables`
- Second instance: `Set Variables 2`
- Third instance: `Set Variables 3`
- If an instance is deleted, its name slot is reused by the next node of that type.

---

## Execution model

Nodes are sorted topologically (Kahn's BFS). Independent nodes at the same depth are grouped into **waves** and executed in parallel using `ThreadPoolExecutor`. The Scheduler node acts as a loop boundary:

- Nodes **before** the Scheduler run once at startup (setup code).
- Nodes **after** the Scheduler run on every loop iteration.

Dataflow semantics:

- Branches remain isolated by predecessor path.
- Branches are only combined at explicit `merge` nodes.
- Final workflow output is computed by **terminal branches** (nodes with no outgoing edges).

Final output contract:

```json
{
  "mode": "by_terminal_branch",
  "branches": {
    "<terminal_node_id>": [ ...items... ]
  },
  "terminals": [
    {"id":"...", "label":"...", "type":"..."}
  ],
  "legacy_items": [ ...flattened items... ]
}
```

When using Scheduler, each loop tick starts with a fresh execution context (`executionId`, `executionDate`) and prints the same structured `final_output` format.

---

## Generate EXE

1. Design the workflow and connect the nodes
2. Click **⚙ Generate EXE**
3. Wait for compilation (may take ~1 minute the first time due to PyInstaller analysis)
4. Download the `.exe` from the result dialog

The executable is standalone (`--onefile`) and does not require Python installed on the target machine.

---

## Project structure

```
workflow-exe/
├── run.py                     # Entry point — starts Flask on :5000
├── requirements.txt           # flask, pyinstaller
├── frontend/                  # React source (Vite)
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api.js             # Fetch helper
│   │   ├── index.css          # Tailwind + CSS custom properties
│   │   ├── context/
│   │   │   └── WorkflowContext.jsx
│   │   ├── hooks/
│   │   │   └── useBuild.js
│   │   ├── nodes/             # React Flow node components + PropsForm
│   │   └── components/        # TopBar, Sidebar, Canvas, PropsPanel, RunPanel, modals
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
├── app/
│   ├── main.py                # Flask app — serves dist/ at /
│   ├── api/
│   │   ├── workflows.py       # Workflow CRUD and graph endpoints
│   │   └── builder.py         # Validate / preview / build / run / download
│   ├── db/
│   │   └── manager.py         # SQLite: main.db + {id}.db per workflow
│   ├── nodes/
│   │   ├── base.py            # Abstract BaseNode
│   │   ├── scheduler.py
│   │   ├── set_variables.py
│   │   ├── get_current_date.py
│   │   ├── add_time_to_date.py
│   │   ├── merge.py
│   │   └── subtract_time_from_date.py
│   ├── codegen/
│   │   └── generator.py       # Topological waves + parallel code generation
│   └── static/
│       └── dist/              # Built React app (generated — do not edit)
├── data/                      # SQLite databases (generated at runtime)
└── output/                    # Compiled .py scripts and .exe files (generated at runtime)
```

---

## REST API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/workflows/` | List all workflows |
| POST | `/api/workflows/` | Create a workflow |
| GET | `/api/workflows/{id}` | Get metadata + graph |
| PUT | `/api/workflows/{id}` | Rename / update metadata |
| DELETE | `/api/workflows/{id}` | Delete workflow and its DB |
| GET | `/api/workflows/{id}/graph` | Get nodes and edges |
| POST | `/api/workflows/{id}/graph` | Save nodes and edges |
| POST | `/api/workflows/{id}/validate` | Validate graph without compiling |
| POST | `/api/workflows/{id}/preview` | Return the generated Python code |
| POST | `/api/workflows/{id}/build` | Start async EXE compilation (returns `job_id`) |
| GET | `/api/workflows/{id}/build/status/{job_id}` | Poll build job status |
| GET | `/api/workflows/{id}/download` | Download the compiled `.exe` |
| POST | `/api/workflows/{id}/run` | Execute workflow and return per-node traces |

`POST /run` response includes:

- `traces`: per-node execution trace
- `output`: raw stdout/stderr
- `final_output`: terminal-branch structured output (`mode`, `branches`, `terminals`, `legacy_items`)

---

## Adding new nodes

### 1. Backend — create the node class

```python
# app/nodes/my_node.py
from __future__ import annotations
from typing import Optional
from app.nodes.base import BaseNode

class MyNode(BaseNode):
    NODE_TYPE = "my_node"

    def validate(self) -> list:
        errors = []
        if not self.config.get("my_field"):
            errors.append("my_field is required")
        return errors

    def to_code(self, indent: int = 0) -> str:
        value = self.config.get("my_field", "")
        return self._indent(f"# my logic: {value}", indent)
```

### 2. Register in the code generator

```python
# app/codegen/generator.py
from app.nodes.my_node import MyNode
NODE_REGISTRY["my_node"] = MyNode
```

### 3. Frontend — create the React node component

```
frontend/src/nodes/MyNode.jsx
```

Export a default canvas component and a named `MyNodePropsForm` component. Follow the pattern of any existing node.

### 4. Register in `frontend/src/nodes/index.js`

Add the node type to `nodeTypes` and its metadata to `NODE_META` (label, icon, inputs, outputs, `defaultConfig`, `PropsForm`).

### 5. Rebuild the frontend

```bash
cd frontend && npm run build
```

---

## Database

Each workflow uses its own SQLite file (`data/{id}.db`) with two tables:

- **nodes** — id, type, label (instance name), position, JSON config
- **edges** — source/target node ids and handle ids

A central file `data/main.db` maintains the registry of all workflows (id, name, description, timestamps).

`save_workflow_graph()` does a full replace (DELETE + INSERT) — it is not a merge.

---

## Deactivate the virtual environment

```bash
deactivate
```
