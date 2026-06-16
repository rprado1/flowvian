# PLANNING4 - Nodo Switch

## 1) Objetivo

Implementar un nodo `switch`, similar a `if`, pero con multiples rutas de salida.

Regla principal:

- Cada condicion define una ruta de salida.
- Solo los items que coincidan con una condicion van a su ruta.
- Los items no coincidentes no van a ninguna ruta (se descartan en este nodo).

---

## 2) Alcance funcional

### Incluido

- Nuevo nodo backend `switch`.
- Configuracion de multiples reglas/condiciones.
- Una salida por regla (dinamica).
- Evaluacion por item con comparaciones tipadas (alineado a `if`/`filter`).
- Integracion con validate/preview/run/build.
- Nodo frontend con handles dinamicos segun numero de rutas.

### No incluido (por ahora)

- Reglas con parentesis o grupos anidados complejos.
- Prioridad configurable por peso (se usara orden de reglas).
- Multiples coincidencias por item (se asigna a la primera coincidencia).

---

## 3) Semantica de ejecucion

Para cada `_item`:

1. Evaluar reglas en orden.
2. Si regla `n` coincide, enviar item a salida `route_n` y detener evaluacion de ese item.
3. Si ninguna coincide, no enrutar item (item descartado).

Resultado:

- `_branch_outputs = {'route_1': [...], 'route_2': [...], ...}`
- `_items` puede construirse como concatenacion de todas las rutas coincidentes para compatibilidad interna.

Decision recomendada:

- **First match wins** (primer match gana).

---

## 4) Contrato de configuracion propuesto

```json
{
  "routes": [
    {
      "name": "High Priority",
      "condition": {
        "input": "${priority}",
        "data_type": "number",
        "operator": "greater_or_equal",
        "compare_value": "8"
      }
    },
    {
      "name": "Medium Priority",
      "condition": {
        "input": "${priority}",
        "data_type": "number",
        "operator": "greater_or_equal",
        "compare_value": "5"
      }
    }
  ],
  "discard_unmatched": true
}
```

Reglas:

- `routes`: lista requerida, minimo 1.
- Cada ruta requiere:
  - `name` (label UI),
  - `condition` con estructura similar a `if`.
- `discard_unmatched`: boolean (default `true`).

---

## 5) Cambios backend

## 5.1 Nuevo nodo

Crear `app/nodes/switch.py` con `SwitchNode(BaseNode)`.

### validate()

- validar existencia de `routes`.
- validar cada condicion como en `if` (`input`, `data_type`, `operator`, `compare_value` cuando aplica).
- validar que no haya nombres de ruta vacios.
- validar `discard_unmatched` boolean.

### to_code()

- Reusar logica de evaluacion tipada del `if` (idealmente helper compartido).
- Inicializar colecciones por ruta:
  - `_route_outputs = {'route_1': [], ...}`
- Iterar items, evaluar rutas en orden y enrutar por primer match.
- Exponer debug:
  - conteo por ruta,
  - total procesados,
  - no coincidentes/descartados.

## 5.2 Registro

Actualizar `app/codegen/generator.py`:

- importar `SwitchNode`.
- registrar en `NODE_REGISTRY`.

---

## 6) Cambios frontend

## 6.1 Componente del nodo

Crear `frontend/src/nodes/SwitchNode.jsx`:

- 1 entrada.
- salidas dinamicas (`route_1...route_n`).
- labels de salida visibles en el nodo.

## 6.2 PropsForm

Formulario debe permitir:

1. Agregar/quitar rutas.
2. Definir nombre de cada ruta.
3. Definir condicion por ruta (misma UX que `if`: tipo, operador, compare).
4. Configurar comportamiento de no coincidencia (descartar sin ruta).

## 6.3 Registro en catalogo

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.switch = SwitchNode`
- `NODE_META.switch` con `defaultConfig`, `inputs`, `outputs` dinamicos y `PropsForm`.

## 6.4 Selector de nodos

- Incluir en categoria `Logic`.

---

## 7) Pruebas sugeridas

## Backend

1. 2 rutas: cada item coincidente cae en ruta esperada.
2. Primer match gana cuando item coincide con multiples rutas.
3. Item sin match no aparece en ninguna ruta (descartado).
4. Validacion de placeholder/tipo/operador por ruta.

## Integracion

5. Flujo `set_variables -> switch -> merge` funciona con ramas correctas.
6. `preview`, `run`, `build` sin regresiones.

## Frontend

7. Handles se actualizan al agregar/quitar rutas.
8. Config persiste tras guardar/cargar.
9. Se puede conectar cada salida a nodos distintos.

---

## 8) Riesgos y mitigaciones

### Riesgos

- Complejidad UI por rutas dinamicas.
- Inconsistencias entre labels visuales y ids de salida.
- Cambios de cantidad de rutas pueden invalidar edges existentes.

### Mitigaciones

- Mantener ids estables (`route_1`, `route_2`, ...).
- Al eliminar ruta, limpiar conexiones invalidas en frontend.
- Reusar estructura de condicion del `if` para reducir bugs.

---

## 9) Resultado esperado

Contar con un nodo `switch` que enrute items por multiples condiciones a salidas distintas, con comportamiento determinista y escalable para flujos con logica de decision avanzada.
