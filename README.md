# WorkflowEXE Builder

Visual tool for creating workflows and compiling them as Windows `.exe` executables.

Design the flow by dragging nodes onto an n8n-style canvas, configure each step, and generate a standalone `.exe` with one click.

---

## Requirements

- Python 3.9+
- Windows (the generated `.exe` is Windows-only)

---

## Installation

**1. Clone the repository and enter the directory:**

```bash
git clone <repo-url>
cd workflow-exe
```

**2. Create the virtual environment:**

```bash
python -m venv .venv
```

**3. Activate the virtual environment:**

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat
```

**4. Install dependencies:**

```bash
pip install -r requirements.txt
```

---

## Usage

With the virtual environment active:

```bash
python run.py
```

Open your browser at `http://localhost:5000`.

> Always run from the project root with the venv active. If the venv is not active, `app.*` imports will fail.

---

## Deactivate the virtual environment

```bash
deactivate
```

---

## Interface

### Top bar
| Element | Description |
|---|---|
| Workflow name | Click to rename |
| **Preview Code** | Shows the Python code that will be generated |
| **Save** | Saves the graph manually (also auto-saved) |
| **Generate EXE** | Compiles the workflow to `.exe` via PyInstaller |

### Left sidebar
- Workflow list: create, select, delete
- Node palette: drag onto the canvas

### Right panel
Appears when clicking a node. Allows configuring its parameters.

---

## Available nodes

### Scheduler
Runs the workflow in a loop with a pause between iterations.

| Field | Type | Description |
|---|---|---|
| Interval | number | Execution frequency |
| Unit | seconds / minutes / hours | Interval unit |

Generates:
```python
_sleep_seconds = 60.0
while True:
    # rest of the workflow
    import time
    time.sleep(_sleep_seconds)
```

### Set Variables
Assigns key=value pairs to the workflow context.

| Field | Description |
|---|---|
| key | Valid Python variable name |
| value | Value (stored as string) |

Generates:
```python
my_variable = 'value'
```

### Get Current Date UTC
Captures the current UTC date/time into a variable.

| Field | Description |
|---|---|
| Output variable name | Name of the result variable |

Generates:
```python
from datetime import datetime, timezone
current_date_utc = datetime.now(timezone.utc)
```

---

## Generate EXE

1. Design the workflow and connect the nodes
2. Click **Generate EXE**
3. Wait for compilation (may take ~1 minute the first time)
4. Download the `.exe` from the result dialog

The executable is standalone (`--onefile`) and does not require Python installed on the target machine.

---

## Project structure

```
workflow-exe/
├── run.py                     # Entry point
├── requirements.txt           # flask, pyinstaller
├── app/
│   ├── main.py                # Flask app
│   ├── api/
│   │   ├── workflows.py       # Workflow CRUD and graph
│   │   └── builder.py        # Validate / preview / build / download
│   ├── db/
│   │   └── manager.py         # SQLite: main.db + {id}.db per workflow
│   ├── nodes/
│   │   ├── base.py            # Abstract BaseNode class
│   │   ├── scheduler.py
│   │   ├── set_variables.py
│   │   └── get_current_date.py
│   ├── codegen/
│   │   └── generator.py       # Topological sort + code generation
│   └── static/                # Frontend (HTML + CSS + JS)
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
| POST | `/api/workflows/{id}/validate` | Validate without compiling |
| POST | `/api/workflows/{id}/preview` | Returns the generated Python code |
| POST | `/api/workflows/{id}/build` | Compile to `.exe` |
| GET | `/api/workflows/{id}/download` | Download the `.exe` |

---

## Adding new nodes

1. Create `app/nodes/my_node.py` extending `BaseNode`:

```python
from app.nodes.base import BaseNode

class MyNode(BaseNode):
    NODE_TYPE = "my_node"

    def validate(self) -> list:
        return []  # return list of errors

    def to_code(self, indent: int = 0) -> str:
        return self._indent("# my logic here", indent)
```

2. Register in `app/codegen/generator.py`:

```python
from app.nodes.my_node import MyNode
NODE_REGISTRY["my_node"] = MyNode
```

3. Create `app/static/js/nodes/my_node.js` with the visual definition and register it in `index.html`.

---

## Database

Each workflow uses its own SQLite file (`data/{id}.db`) with two tables:

- **nodes** — id, type, position, JSON configuration
- **edges** — connections between nodes

A central file `data/main.db` maintains the registry of all workflows.
