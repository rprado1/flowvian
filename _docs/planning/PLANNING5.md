# PLANNING — Req #7, #8, #9 Fase 2: Flujo de datos como Array + Execution ID + n-items

## Requerimientos

| # | Requerimiento |
|---|---------------|
| 7 | El flujo de datos en cada nodo debe ser un array. El primer nodo debe tener como entrada `[{"workflowId","executionId","executionDate"}]` |
| 8 | El `executionId` es un ID random único de ejecución |
| 9 | Cada nodo se debe ejecutar para los n items en el flujo actual |

**Regla adicional definida por el usuario:**
- Cada nodo produce una salida con **solo sus propios campos** (sin heredar campos del flujo).
- Checkbox **"Include Other Input Fields"** en cada nodo de datos: si se marca, el output hereda todos los campos del input + agrega los suyos.

---

## Diagnóstico actual

| Aspecto | Estado |
|---|---|
| Transporte de datos entre nodos | Variables sueltas en scope Python compartido (`my_var = "x"`) |
| Contexto de ejecución | No existe `workflowId`, `executionId`, `executionDate` |
| Iteración por items | No existe — cada nodo ejecuta una sola vez por iteración del loop |
| Trazas (Run) | Capturan `locals()` antes/después del nodo |

---

## Arquitectura objetivo

### Modelo de datos: pipeline de items

```
_items = [{workflowId, executionId, executionDate}]   ← init (req #7, #8)
         ↓
    ┌─────────────────────────────────────┐
    │  Nodo de datos                      │
    │                                     │
    │  _items_out = []                    │
    │  for _item in _items:               │  ← itera sobre n items (req #9)
    │      _out = {}                      │
    │      _out["campo"] = resultado      │  ← solo campos propios
    │      if include_other_input_fields: │  ← checkbox
    │          _out = {**_item, **_out}   │
    │      _items_out.append(_out)        │
    │  _items = _items_out                │
    └─────────────────────────────────────┘
         ↓
    _items = [{campo: resultado, ...}]     ← pasa al siguiente nodo
```

### Ejemplo de flujo con 3 nodos

```
Inicial:             [{workflowId:"abc", executionId:"e1", executionDate:"2026-..."}]

Set Variables        (include=false)
  Input:             [{workflowId, executionId, executionDate}]
  Output:            [{my_var:"hello"}]

Get Current Date     (include=true)
  Input:             [{my_var:"hello"}]
  Output:            [{my_var:"hello", current_date_utc:"2026-..."}]

Add Time to Date     (include=false)
  Input:             [{my_var:"hello", current_date_utc:"2026-..."}]
  Output:            [{new_date:"2026-..."}]
```

### Ejecución paralela (waves)

En waves multi-nodo, cada branch de la wave recibe una **copia independiente** de `_items`. El último branch que termina define `_items` final (los cambios de otros branches se pierden).

```python
def _wave_0_branch_0():
    _w_items = list(_items)    # copia independiente
    _items_out = []
    for _item in _w_items:
        _out = {}
        _out["a"] = 1
        _items_out.append(_out)
    _w_items = _items_out
    # ... al terminar, _w_items del último branch define el resultado

def _wave_0_branch_1():
    _w_items = list(_items)    # copia independiente
    _items_out = []
    for _item in _w_items:
        _out = {}
        _out["b"] = 2
        _items_out.append(_out)
    _items = _items_out         # último branch → define _items global
```

---

## Cambios necesarios

### 1. Backend — Nodos

#### 1.1 `app/nodes/base.py`

Agregar helper `_emit_item_loop(code_body, indent, include_flag=True)` que genera:

```python
_items_out = []
for _item in _items:
    _out = {}
    {code_body}
    if {include_flag}:
        _out = {{**_item, **_out}}
    _items_out.append(_out)
_items = _items_out
```

#### 1.2 `app/nodes/scheduler.py`

Sin cambios. El Scheduler es estructural (no procesa datos). `validate()` debe aceptar pero ignorar `include_other_input_fields` si llega a estar presente en el config.

#### 1.3 `app/nodes/set_variables.py`

`to_code()` actual:
```python
lines.append(f"{key} = {repr(str(value))}")
```
Nuevo:
```python
lines.append(f'_out[{repr(key)}] = {repr(str(value))}')
```

Agregar campo `include_other_input_fields: bool` (default `False`) en `validate()`.

#### 1.4 `app/nodes/get_current_date.py`

`to_code()` actual:
```python
lines.append(f"{output_var} = datetime.now(timezone.utc)")
```
Nuevo:
```python
lines.append(f'_out[{repr(output_var)}] = datetime.now(timezone.utc).isoformat()')
```

Las fechas se serializan a string ISO 8601 para ser transportables en el array de items.

Agregar campo `include_other_input_fields: bool` (default `False`) en `validate()`.

#### 1.5 `app/nodes/add_time_to_date.py`

`to_code()` actual:
```python
f"{output_var} = {input_var} + timedelta({delta_args})"
```
Nuevo:
```python
_input_val = datetime.fromisoformat(_item[{repr(input_var)}])
_out[{repr(output_var)}] = (_input_val + timedelta({delta_args})).isoformat()
```

Requiere importar `datetime` (la clase, no solo el módulo) en el código generado.

Agregar campo `include_other_input_fields: bool` (default `False`) en `validate()`.

#### 1.6 `app/nodes/subtract_time_from_date.py`

Ídem que `add_time_to_date.py` pero con resta (`- timedelta`).

---

### 2. Backend — Codegen

#### 2.1 `app/codegen/generator.py`

**`SCRIPT_HEADER`** — Agregar imports:
```python
import uuid
from datetime import datetime, timezone
```

**`generate_script()`** — Nuevo parámetro `workflow_id`:
```python
def generate_script(workflow_name: str, workflow_id: str, nodes: list[dict], edges: list[dict]) -> str:
```

Emitir inicialización después del header:
```python
WORKFLOW_ID = "<workflow_id>"
EXECUTION_ID = str(uuid.uuid4())
_items = [{
    "workflowId": WORKFLOW_ID,
    "executionId": EXECUTION_ID,
    "executionDate": datetime.now(timezone.utc).isoformat()
}]
```

**`_emit_waves()`** — Envolver cada nodo en el item loop. El flag `include_other_input_fields` se lee del config del nodo.

Para waves multi-nodo (ThreadPoolExecutor), cada branch function recibe copia independiente:
```python
def _wave_0_branch_0():
    _w_items = list(_items)
    _items_out = []
    for _item in _w_items:
        _out = {}
        # ... node code ...
        if {include_flag}:
            _out = {**_item, **_out}
        _items_out.append(_out)
    _w_items = _items_out

def _wave_0_branch_1():
    _w_items = list(_items)
    _items_out = []
    for _item in _w_items:
        _out = {}
        # ... node code ...
        if {include_flag}:
            _out = {**_item, **_out}
        _items_out.append(_out)
    _items = _items_out   # último branch define _items
```

**`generate_run_script()`** — Nuevo parámetro `workflow_id`. Trazas cambian de snapshot de `locals()` a snapshot de items:
```python
_trace.append({
    'id': node_id,
    'type': node_type,
    'label': node_label,
    'status': 'ok',
    'ts': time.time(),
    'items_in': list(_items_before),
    'items_out': list(_items_after),
})
```

**`validate_graph()`** — Sin cambios.

---

### 3. Backend — API

#### 3.1 `app/api/builder.py`

- `preview`: `generate_script(meta["name"], workflow_id, ...)`
- `build`: `generate_script(meta["name"], workflow_id, ...)` + worker recibe `workflow_id`
- `run_workflow`: `generate_run_script(meta["name"], workflow_id, ...)`

Cambio en `subprocess.Popen` del build:
```python
subprocess.Popen(
    [sys.executable, worker_path,
     job_file, script_path, safe_name, dist_dir, work_dir, spec_dir, workflow_id],
    ...
)
```

#### 3.2 `app/build_worker.py`

Aceptar `workflow_id` como 8º argumento (`sys.argv[8]`). Insertarlo en el script generado (el script ya lo tendrá inline del generador — verificar que no requiera paso adicional).

---

### 4. Frontend — Nodos

#### 4.1 PropsForm de cada nodo de datos

Agregar checkbox "Include Other Input Fields" al final de cada formulario:

```jsx
<div className="flex items-center gap-2 pt-2">
  <Checkbox
    id="include-input-fields"
    checked={config.include_other_input_fields || false}
    onCheckedChange={(checked) =>
      onChange({ ...config, include_other_input_fields: checked })
    }
  />
  <Label
    htmlFor="include-input-fields"
    className="text-sm text-muted-foreground cursor-pointer"
  >
    Include Other Input Fields
  </Label>
</div>
```

Archivos:
- `frontend/src/nodes/SetVariablesNode.jsx`
- `frontend/src/nodes/GetCurrentDateNode.jsx`
- `frontend/src/nodes/AddTimeToDateNode.jsx`
- `frontend/src/nodes/SubtractTimeFromDateNode.jsx`

Requiere importar `Checkbox` desde `@/components/ui/checkbox`. Si no existe el componente, crearlo con shadcn: `npx shadcn-ui@latest add checkbox`.

#### 4.2 `frontend/src/nodes/index.js`

Agregar `include_other_input_fields: false` en `defaultConfig()` de los 4 nodos de datos.

Scheduler no lo incluye (nodo estructural).

---

### 5. Frontend — Run Panel

#### 5.1 `frontend/src/components/RunPanel.jsx`

Las trazas ahora contienen `items_in` e `items_out` (arrays) en lugar de `input`/`output` (dicts de variables).

Reemplazar `fmtCtx()` por `fmtItems(items)`:
```jsx
function fmtItems(items) {
  if (!items || !items.length) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="block">
      <span className="text-muted-foreground">{items.length} item{items.length !== 1 ? 's' : ''}</span>
      {items.slice(0, 3).map((item, i) => (
        <span key={i} className="block text-xs mt-0.5">
          {Object.entries(item).slice(0, 5).map(([k, v]) => {
            let val = String(v ?? '');
            if (val.length > 40) val = val.substring(0, 37) + '…';
            return <span key={k} className="block"><code className="run-ctx">{k}</code> = {val}</span>;
          })}
        </span>
      ))}
      {items.length > 3 && <span className="text-xs text-muted-foreground">+{items.length - 3} more</span>}
    </span>
  );
}
```

Columnas de la tabla cambian de `Input`/`Output` a `Items In`/`Items Out`.

---

## Resumen de archivos

| # | Archivo | Tipo de cambio |
|---|---------|----------------|
| 1 | `app/nodes/base.py` | Agregar helper `_emit_item_loop()` |
| 2 | `app/nodes/set_variables.py` | `to_code()` → `_out[key]`; aceptar `include_other_input_fields` |
| 3 | `app/nodes/get_current_date.py` | `to_code()` → `_out[var] = ...isoformat()`; ídem |
| 4 | `app/nodes/add_time_to_date.py` | `to_code()` → opera sobre `_item`/`_out` con `datetime.fromisoformat`; ídem |
| 5 | `app/nodes/subtract_time_from_date.py` | Ídem que add_time |
| 6 | `app/codegen/generator.py` | Init `_items`, wrapper `for _item`, nuevo trace, recibir `workflow_id` |
| 7 | `app/api/builder.py` | Pasar `workflow_id` a generadores + worker |
| 8 | `app/build_worker.py` | Recibir `workflow_id` como argumento |
| 9 | `frontend/src/nodes/SetVariablesNode.jsx` | Checkbox "Include Other Input Fields" |
| 10 | `frontend/src/nodes/GetCurrentDateNode.jsx` | Ídem |
| 11 | `frontend/src/nodes/AddTimeToDateNode.jsx` | Ídem |
| 12 | `frontend/src/nodes/SubtractTimeFromDateNode.jsx` | Ídem |
| 13 | `frontend/src/nodes/index.js` | `include_other_input_fields: false` en defaultConfig |
| 14 | `frontend/src/components/RunPanel.jsx` | Adaptar a `items_in`/`items_out` |

---

## Orden de implementación

1. `app/nodes/base.py` — helper `_emit_item_loop()`
2. `app/nodes/*.py` (4 nodos de datos) — nuevo `to_code()` + validar nuevo campo
3. `app/codegen/generator.py` — init items + wrapper + trace + `workflow_id`
4. `app/api/builder.py` + `app/build_worker.py` — pasar `workflow_id`
5. Verificar backend: `python -c "from app.main import app; print('OK')"`
6. `frontend/src/nodes/index.js` — defaultConfig
7. `frontend/src/nodes/*Node.jsx` (4 PropsForm) — checkbox
8. `frontend/src/components/RunPanel.jsx` — adaptar visualización
9. `cd frontend && npm run build`

---

## Verificación

1. `python -c "from app.main import app; print('OK')"` → sin errores de importación
2. Crear workflow con 1 nodo Set Variables → Preview muestra código con `_items` inicial y `for _item in _items:`
3. El código generado incluye `WORKFLOW_ID`, `EXECUTION_ID = str(uuid.uuid4())`, y `datetime.now(timezone.utc).isoformat()`
4. Run con 1 nodo → traza muestra `items_in` e `items_out` (arrays, no dicts de variables)
5. `items_in` del primer nodo contiene `workflowId`, `executionId`, `executionDate`
6. `items_out` del primer nodo contiene solo los campos propios del nodo (si checkbox=false)
7. Workflow con 2 nodos encadenados (Set Variables → Get Current Date):
   - Nodo 1 (include=false): items_out = `[{my_var: "hello"}]`
   - Nodo 2 (include=true): items_out = `[{my_var: "hello", current_date_utc: "..."}]`
8. Workflow con Scheduler → items persisten entre iteraciones
9. Generar EXE → ejecuta correctamente con el nuevo modelo de items
