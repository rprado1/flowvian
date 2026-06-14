# PLANNING7 — Merge con N ramas configurables

## Objetivo

- Cumplir requerimiento 12: el nodo `merge` debe concatenar **N ramas**.
- El usuario define `N` en la configuración del nodo (`branch_count`).
- El `merge` mantiene estrategia única `append`.

---

## 1. Diseño funcional

### Regla principal

- `merge` recibe `branch_count` (entero >= 2).
- El nodo debe tener exactamente `branch_count` entradas conectadas.
- El output del `merge` es la concatenación (append) de los items de cada rama de entrada.

### Comportamiento esperado

- Si `branch_count = 3`, el nodo mostrará 3 handles de entrada.
- Si faltan ramas conectadas al construir/ejecutar, la validación falla.
- Si sobran conexiones respecto a `branch_count`, la validación falla.

---

## 2. Backend

### 2.1 `app/nodes/merge.py`

- Agregar validación de `branch_count`:
  - tipo numérico entero
  - mínimo `2`
- Mantener `strategy` fija en `append`.

Ejemplo esperado en `validate()`:

```python
strategy = self.config.get("strategy", "append")
if strategy != "append":
    errors.append(...)

branch_count_raw = self.config.get("branch_count", 2)
try:
    branch_count = int(branch_count_raw)
    if branch_count < 2:
        errors.append(...)
except (TypeError, ValueError):
    errors.append(...)
```

### 2.2 `app/codegen/generator.py` — validación de entradas

En `validate_graph()`:

1. Mantener regla existente: solo `merge` puede tener múltiples incoming edges.
2. Para cada nodo `merge`, comparar:
   - `incoming_count[node_id]`
   - `config.branch_count` (default 2)
3. Si no coincide, devolver error claro.

Ejemplo de error:

```text
[Merge] merge requires 3 incoming edges (has 2)
```

### 2.3 `app/codegen/generator.py` — ejecución

- No cambia la semántica base ya implementada en PLANNING6:
  - aislamiento de ramas
  - unión explícita en `merge`
- Asegurar que el `append` del merge use todas sus ramas predecesoras.

---

## 3. Frontend

### 3.1 `frontend/src/nodes/MergeNode.jsx`

- Reemplazar entradas fijas (`in-0`, `in-1`) por entradas dinámicas:
  - leer `branch_count` desde `data.config`
  - renderizar N handles target

Ejemplo conceptual:

```jsx
const branchCount = Math.max(2, parseInt(data.config?.branch_count ?? 2, 10) || 2)
for (let i = 0; i < branchCount; i++) {
  // <Handle type="target" id={`in-${i}`} ... />
}
```

- Distribuir los handles verticalmente de forma proporcional (top %).

### 3.2 `MergePropsForm`

- Agregar input numérico `branch_count`:
  - mínimo `2`
  - paso `1`
  - valor por defecto `2`
- Mantener select de `strategy` en solo `append` (bloqueado a una opción).

### 3.3 `frontend/src/nodes/index.js`

- Actualizar `defaultConfig` de `merge`:

```js
defaultConfig: () => ({ strategy: 'append', branch_count: 2 })
```

---

## 4. Integración de grafo

### `frontend/src/components/Canvas.jsx`

- Mantener creación de edges como hoy.
- No se requiere lógica especial si los handles dinámicos están bien definidos.
- (Opcional recomendado) bloquear conexión duplicada al mismo handle target.

---

## 5. Dependencias y orden

| Paso | Archivo | Depende de |
|---|---|---|
| 1 | `app/nodes/merge.py` | — |
| 2 | `app/codegen/generator.py` (validate_graph) | 1 |
| 3 | `frontend/src/nodes/MergeNode.jsx` | — |
| 4 | `frontend/src/nodes/index.js` | 3 |
| 5 | Verificación end-to-end | 1,2,3,4 |

Orden sugerido: 1 → 2 → 3 → 4 → 5

---

## 6. Verificación

```bash
# Backend
python -c "from app.main import app; print('OK')"

# Validación de merge con branch_count=3 y 2 entradas (debe fallar)
python -c "from app.codegen.generator import validate_graph; nodes=[{'id':'m','type':'merge','label':'Merge','config':{'strategy':'append','branch_count':3}}]; edges=[{'source_node_id':'a','target_node_id':'m'},{'source_node_id':'b','target_node_id':'m'}]; print(validate_graph(nodes, edges))"

# Validación con branch_count=3 y 3 entradas (debe pasar)
python -c "from app.codegen.generator import validate_graph; nodes=[{'id':'m','type':'merge','label':'Merge','config':{'strategy':'append','branch_count':3}},{'id':'a','type':'set_variables','label':'A','config':{'variables':[{'key':'a','value':'1'}]}},{'id':'b','type':'set_variables','label':'B','config':{'variables':[{'key':'b','value':'2'}]}},{'id':'c','type':'set_variables','label':'C','config':{'variables':[{'key':'c','value':'3'}]}}]; edges=[{'source_node_id':'a','target_node_id':'m'},{'source_node_id':'b','target_node_id':'m'},{'source_node_id':'c','target_node_id':'m'}]; print(validate_graph(nodes, edges))"

# Frontend
cd frontend && npm run build
```

---

## 7. Riesgos y mitigación

- Riesgo: `branch_count` cambia y quedan conexiones inválidas.
  - Mitigación: validar en backend (fuente de verdad) y opcionalmente mostrar advertencia en UI.
- Riesgo: demasiados handles hacen el nodo poco usable visualmente.
  - Mitigación: límite razonable (p.ej. 2..12) o scroll/altura mínima dinámica.

---

## 8. Criterio de aceptación

- Existe input de configuración para número de ramas en `merge`.
- El nodo renderiza N entradas según configuración.
- Build/Run falla si las entradas conectadas no coinciden con `branch_count`.
- Con entradas correctas, `merge` concatena todas las ramas con estrategia `append`.
