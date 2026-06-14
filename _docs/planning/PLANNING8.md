# PLANNING8 — Correccion de conexiones en Merge con handles dinamicos

## Objetivo

Corregir el comportamiento de conexiones del nodo `merge` cuando `branch_count > 2`, para asegurar que:

- cada linea se ancle exactamente al handle visible,
- no se creen conexiones intermedias o huerfanas,
- la validacion backend no reciba edges extra por `targetHandle` vacio,
- con `branch_count = N`, el merge acepte como maximo `N` conexiones entrantes validas (una por handle `in-0 ... in-(N-1)`).

---

## Problema actual

El error reportado (`merge requires 3 incoming edges (has 4)`) se explica por una combinacion de causas en frontend:

1. En `MergeNode`, los handles cambian dinamicamente, pero React Flow no siempre recalcula la geometria interna al cambiar `branch_count`.
2. En `onConnect`, se aceptan conexiones cuando `targetHandle` o `sourceHandle` llegan vacios/null.
3. En persistencia (`WorkflowContext.saveGraph`), un `targetHandle` vacio cae en fallback `input_1`, lo que contamina el grafo de `merge` (que usa `in-*`).

---

## Alcance de cambios

### 1) `frontend/src/nodes/MergeNode.jsx`

- Cambiar firma a `function MergeNode({ id, data })`.
- Importar y usar `useEffect` + `useUpdateNodeInternals` desde React Flow.
- Llamar `updateNodeInternals(id)` cada vez que cambie `branchCount`.
- Mantener handles `in-${idx}` y distribucion vertical actual.

Resultado esperado: el hitbox real de cada handle coincide con su posicion visual despues de cambiar `branch_count`.

---

### 2) `frontend/src/components/Canvas.jsx`

#### 2.1 Endurecer `onConnect`

- Rechazar conexion si:
  - `!params.sourceHandle`
  - `!params.targetHandle`
- Evitar duplicado exacto (`source`, `target`, `sourceHandle`, `targetHandle`).
- Evitar mas de una conexion al mismo `target + targetHandle` (single-occupancy por entrada de merge).

#### 2.2 Validar durante drag

- Agregar `isValidConnection` para bloquear conexiones invalidas antes de soltar.
- Reglas minimas:
  - requiere `sourceHandle` y `targetHandle` no vacios,
  - no duplicados,
  - no mas de 1 edge por `target + targetHandle`.

#### 2.3 Modo de conexion estricto

- En `<ReactFlow ... />`, habilitar `connectionMode={ConnectionMode.Strict}`.

Resultado esperado: solo se puede conectar sobre handles reales y validos.

---

### 3) `frontend/src/context/WorkflowContext.jsx`

- Ajustar mapeo de edges en `saveGraph`:
  - no usar fallback ciego `targetHandle || 'input_1'` para todos los casos.
  - persistir `target_input` solo si existe handle valido.
- Mantener compatibilidad para nodos legacy (no merge), pero evitar crear `input_1` artificial cuando el target es `merge`.

Opcion recomendada:

- bloquear edges sin handles en `onConnect`,
- y adicionalmente filtrar en `saveGraph` edges con handles incompletos para evitar persistir basura.

---

### 4) Limpieza de datos existentes

Para workflows ya afectados:

- Eliminar conexiones entrantes del nodo `merge` afectado y reconectar manualmente despues del fix.
- Si existen registros guardados con `target_input='input_1'` apuntando a `merge`, regenerar esas conexiones.

No se requiere migracion automatica obligatoria en esta iteracion.

---

## Dependencias y orden de implementacion

| Paso | Archivo | Depende de |
|---|---|---|
| 1 | `frontend/src/nodes/MergeNode.jsx` | — |
| 2 | `frontend/src/components/Canvas.jsx` (onConnect + isValidConnection + Strict mode) | 1 |
| 3 | `frontend/src/context/WorkflowContext.jsx` (persistencia defensiva) | 2 |
| 4 | Verificacion manual + build | 1,2,3 |

Orden sugerido: **1 -> 2 -> 3 -> 4**

---

## Verificacion

### A. Build

```bash
cd frontend && npm run build
```

### B. Prueba funcional UI (caso principal)

1. Crear nodo `merge` con `branch_count = 3`.
2. Conectar 3 ramas distintas a `in-0`, `in-1`, `in-2`.
3. Confirmar que cada edge ancla sobre el handle exacto (sin desplazamientos intermedios).
4. Intentar conectar una cuarta rama:
   - debe bloquearse en UI, o
   - no debe persistirse.

### C. Persistencia

1. Guardar workflow.
2. Recargar pagina.
3. Verificar que las conexiones preservan `targetHandle` correcto (`in-0`, `in-1`, `in-2`).
4. Ejecutar build/run y confirmar que no aparece `has 4` cuando visualmente hay 3.

### D. Regresion

- Verificar que nodos no-merge siguen conectando normal con `input_1`.
- Verificar que merge con `branch_count=2` mantiene comportamiento previo esperado.

---

## Criterio de aceptacion

- Al cambiar `branch_count`, los handles de `merge` son clickeables en su posicion visible real.
- No se crean edges con `targetHandle` vacio/null.
- No se permiten duplicados exactos ni doble ocupacion del mismo `targetHandle`.
- La validacion backend deja de reportar falsos positivos por conexiones fantasma (ej. `has 4` con 3 ramas visibles).
- Se mantiene compatibilidad con nodos existentes y flujo actual.
