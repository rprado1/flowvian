# PLANNING11 — Nodo Wait (segundos)

## Objetivo

Implementar un nuevo nodo `wait` que pause la ejecución del flujo por una cantidad de segundos configurable.

Alcance de este requerimiento:

- Unidad única: **segundos**.
- Debe funcionar en ejecución normal, `Run` desde portal y `.exe` generado.
- Debe integrarse al sistema de nodos backend/frontend existente.

---

## Requerimiento funcional

- Nuevo tipo de nodo: `wait`
- Configuración:
  - `seconds` (número)
  - valor mínimo: `0`
  - default recomendado: `1`
- Comportamiento:
  - Si `seconds > 0`, ejecutar `time.sleep(seconds)`
  - Si `seconds == 0`, no pausar
- El nodo no transforma campos; solo introduce demora en el flujo.

---

## Diseño técnico

## 1) Backend

### 1.1 Crear nodo

Archivo nuevo: `app/nodes/wait.py`

Clase: `WaitNode(BaseNode)`

- `NODE_TYPE = "wait"`
- `validate()`:
  - `seconds` debe ser numérico
  - `seconds >= 0`
  - mensajes claros:
    - `wait: seconds must be a number`
    - `wait: seconds must be greater than or equal to 0`
- `to_code(indent=0)`:
  - generar código con comentario `# Wait`
  - usar `time.sleep(<seconds>)`
  - incluir `import time` en el bloque emitido (siguiendo patrón actual de nodos)

Ejemplo de bloque emitido:

```python
# Wait
import time
time.sleep(2.0)
```

### 1.2 Registrar nodo en codegen

Archivo: `app/codegen/generator.py`

- Importar `WaitNode`
- Agregar `WaitNode.NODE_TYPE: WaitNode` a `NODE_REGISTRY`

No se requieren cambios especiales en `_emit_waves()` ni en validación de merges.

---

## 2) Frontend

### 2.1 Crear componente de nodo

Archivo nuevo: `frontend/src/nodes/WaitNode.jsx`

Debe exportar:

- `default` componente canvas
- `WaitPropsForm` para propiedades

Canvas:

- UI simple con icono sugerido `⏳`
- `inputs=1`, `outputs=1`
- Mostrar texto `Wait <seconds>s`

Props form:

- Input numérico `seconds`
- `min={0}`
- Parse robusto con fallback a `1`

### 2.2 Registrar en índice de nodos

Archivo: `frontend/src/nodes/index.js`

- Importar `WaitNode` y `WaitPropsForm`
- Agregar en `nodeTypes`:
  - `wait: WaitNode`
- Agregar en `NODE_META`:
  - `label: 'Wait'`
  - `icon: '⏳'`
  - `description: 'Pause for N seconds'`
  - `inputs: 1`
  - `outputs: 1`
  - `defaultConfig: () => ({ seconds: 1 })`
  - `PropsForm: WaitPropsForm`

---

## 3) Validaciones esperadas

- `seconds = 0` -> válido
- `seconds = 1.5` -> válido
- `seconds = -1` -> inválido
- `seconds = "abc"` -> inválido

---

## 4) Verificación

### Backend

```bash
python -c "from app.main import app; print('OK')"
python -m py_compile app/nodes/wait.py app/codegen/generator.py
```

Smoke de validación:

```bash
python -c "from app.codegen.generator import validate_graph; print(validate_graph([{'id':'w1','type':'wait','label':'Wait','config':{'seconds':2}}], []))"
```

### Frontend

```bash
cd frontend && npm run build
```

### Flujo funcional

1. Crear flujo: `Set Variables -> Wait -> Set Variables`
2. Configurar `Wait.seconds = 2`
3. Ejecutar `Run` desde portal y confirmar demora aproximada
4. Generar `.exe` y confirmar misma demora

---

## 5) Criterio de aceptación

- El nodo `Wait` aparece en palette y puede configurarse por segundos.
- El grafo valida correctamente según reglas de `seconds`.
- El código generado incluye pausa por segundos.
- `Run` y `.exe` respetan la espera configurada.
- No rompe nodos existentes ni el flujo de build.
