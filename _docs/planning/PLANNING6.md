# PLANNING6 — Nuevo nodo Merge + corrección de ramas paralelas

## Objetivo

- Ningún nodo (excepto `merge`) puede tener más de 1 incoming edge
- Nuevo nodo `merge` que consolida items de múltiples ramas
- Arreglar la pérdida de datos en waves multi-nodo (solo la última rama sobrevivía)

---

## 1. Backend — Nuevo nodo `merge`

### `app/nodes/merge.py` (nuevo archivo)

```python
from app.nodes.base import BaseNode

class MergeNode(BaseNode):
    NODE_TYPE = "merge"

    def validate(self) -> list[str]:
        errors = []
        strategy = self.config.get("strategy", "append")
        if strategy not in ("append",):
            errors.append(f"merge: unknown strategy '{strategy}'")
        return errors

    def to_code(self, indent: int = 0) -> str:
        code_body = (
            "# Merge: append items from all inbound branches\n"
            "pass"
        )
        return self._indent(code_body, indent)
```

### `app/codegen/generator.py`

#### a) Registrar en `NODE_REGISTRY` (~línea 24)

```python
from app.nodes.merge import MergeNode

NODE_REGISTRY = {
    ...
    MergeNode.NODE_TYPE: MergeNode,
}
```

#### b) Fix multi-node wave (~líneas 174-215) — recolectar TODAS las ramas

Reemplazar el bloque `else:` (multi-node wave) para que:

1. Antes de definir branches: `_wave_{w_idx}_results = []`
2. En cada branch, después del node code: `_wave_{w_idx}_results.append(list(_items))`
3. Después del `ThreadPoolExecutor`, mergear:
   ```python
   _items = []
   for _r in _wave_{w_idx}_results:
       _items.extend(_r)
   ```

Esto se aplica TANTO para instrument=True como instrument=False.

#### c) Validación — solo `merge` permite >1 incoming edge

En `validate_graph()`, agregar:

```python
# Build incoming-edge count
incoming_count = defaultdict(int)
for edge in edges:
    incoming_count[edge["target_node_id"]] += 1

for node_data in nodes:
    nid = node_data["id"]
    if incoming_count[nid] > 1 and node_data["type"] != "merge":
        errors.append(
            f"[{node_data.get('label', nid)}] "
            f"Only 'merge' nodes can have multiple incoming edges "
            f"(has {incoming_count[nid]})"
        )
```

---

## 2. Frontend — Componente MergeNode

### `frontend/src/nodes/MergeNode.jsx` (nuevo)

```jsx
import { Handle, Position } from 'reactflow';

export default function MergeNode({ data }) {
  return (
    <div className="node-box merge-node" style={{ borderColor: '#f59e0b' }}>
      <div className="node-header" style={{ background: '#f59e0b' }}>
        <span>⬡ Merge</span>
      </div>
      <div className="node-body">
        <span className="text-xs text-muted-foreground">
          {data.instanceName || 'Merge'}
        </span>
      </div>
      <Handle type="target" position={Position.Left} id="in-0" style={{ top: '30%' }} />
      <Handle type="target" position={Position.Left} id="in-1" style={{ top: '70%' }} />
      <Handle type="source" position={Position.Right} id="out" />
    </div>
  );
}

export function MergePropsForm({ config, onChange }) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-medium">Strategy</label>
      <select
        value={config.strategy || 'append'}
        onChange={e => onChange({ ...config, strategy: e.target.value })}
        className="w-full text-xs"
      >
        <option value="append">Append</option>
      </select>
    </div>
  );
}
```

### `frontend/src/nodes/index.js`

Agregar:

```js
import MergeNode, { MergePropsForm } from './MergeNode';

// En nodeTypes:
merge: MergeNode,

// En NODE_META:
merge: {
  label: 'Merge',
  icon: '⬡',
  inputs: 2,
  outputs: 1,
  defaultConfig: () => ({ strategy: 'append' }),
  PropsForm: MergePropsForm,
},
```

---

## 3. Dependencias

| Paso | Archivo | Depende de |
|---|---|---|
| 1a | `app/nodes/merge.py` | — |
| 1b | `app/codegen/generator.py` (NODE_REGISTRY) | 1a |
| 1c | `app/codegen/generator.py` (_emit_waves) | — |
| 1d | `app/codegen/generator.py` (validate_graph) | — |
| 2a | `frontend/src/nodes/MergeNode.jsx` | — |
| 2b | `frontend/src/nodes/index.js` | 2a |

Orden de implementación: 1a → 1b → 1c → 1d → 2a → 2b

---

## 4. Verificación

```bash
# Backend
python -c "from app.main import app; print('OK')"

# Smoke test con merge node
python -c "
from app.codegen.generator import generate_script, validate_graph
nodes = [
    {'id': 'a', 'type': 'set_variables', 'label': 'Set A', 'config': {'variables': [{'key': 'x', 'value': '1'}]}},
    {'id': 'b', 'type': 'set_variables', 'label': 'Set B', 'config': {'variables': [{'key': 'y', 'value': '2'}]}},
    {'id': 'm', 'type': 'merge', 'label': 'Merge', 'config': {}},
    {'id': 'c', 'type': 'set_variables', 'label': 'Set C', 'config': {'variables': [{'key': 'z', 'value': '3'}]}},
]
edges = [
    {'source_node_id': 'a', 'target_node_id': 'm'},
    {'source_node_id': 'b', 'target_node_id': 'm'},
    {'source_node_id': 'm', 'target_node_id': 'c'},
]
script = generate_script('test', 'wf123', nodes, edges)
print(script)
"

# Frontend
cd frontend && npm run build
```
