# PLANNING4 — Nodo IF (condicional con salidas True/False)

## Objetivo

Diseñar e implementar un nuevo nodo `if` para el motor de workflows que evalúe una condición por cada `_item` y enrute el resultado por dos salidas exclusivas:

- `true`
- `false`

Este documento define la propuesta funcional y técnica para implementación. **No implementa código en esta etapa.**

---

## Requerimiento funcional

El nodo IF debe permitir configurar:

1. **Variable a evaluar**
   - Input con sintaxis `${VARIABLE}`.
   - Se resuelve en runtime usando el `_item` actual.

2. **Condición**
   - Selector de operador.
   - Operadores visibles según el tipo de dato.

3. **Valor de comparación**
   - Puede ser literal o `${VARIABLE}`.
   - Para operadores unarios (ej. `is_true`, `is_empty`) este campo no se usa.

Tipos soportados:

- `string`
- `number`
- `boolean`
- `object`
- `array`

Resultado:

- Si cumple condición -> salida `true`
- Si no cumple -> salida `false`

---

## Alcance

## Incluido

1. Nuevo nodo backend `if` con validación y generación de código.
2. Nuevo nodo frontend con formulario y operadores dinámicos por tipo.
3. Soporte de `${VARIABLE}` en variable evaluada y valor de comparación.
4. Validación de compatibilidad de tipos con errores descriptivos.
5. Soporte de enrutamiento por handle de salida (`true` / `false`) en ejecución.

## No incluido (fase futura)

- Expresiones compuestas (`AND/OR`, paréntesis, múltiples reglas).
- Comparadores regex para strings.
- Coerción implícita agresiva entre tipos distintos.

---

## Diseño funcional propuesto

## Config del nodo

```json
{
  "input": "${country}",
  "data_type": "string",
  "operator": "equals",
  "compare_value": "EC"
}
```

Notas:

- `input` es obligatorio y debe ser placeholder exacto `${...}`.
- `compare_value` puede ser literal o `${...}`.
- `compare_value` puede omitirse en operadores unarios.

## Operadores por tipo

### String

- `equals`
- `not_equals`
- `contains`
- `not_contains`
- `starts_with`
- `ends_with`
- `is_empty`
- `is_not_empty`

### Number

- `equals`
- `not_equals`
- `greater_than`
- `less_than`
- `greater_or_equal`
- `less_or_equal`

### Boolean

- `is_true`
- `is_false`

### Object

- `exists`
- `not_exists`
- `has_property`
- `not_has_property`

### Array

- `is_empty`
- `is_not_empty`
- `length_equals`
- `length_greater_than`
- `length_less_than`

---

## Reglas de resolución y tipos

1. Resolver `input`:
   - `${VAR}` exacto -> usar `_item[VAR]` (preservando tipo).
   - Si no existe -> error descriptivo.

2. Resolver `compare_value` (si aplica):
   - `${VAR}` exacto -> usar `_item[VAR]` preservando tipo.
   - Texto con placeholders embebidos -> string interpolado.
   - Literal sin placeholder -> parsear según `data_type` cuando corresponda.

3. Compatibilidad:
   - `string` compara contra string.
   - `number` compara contra número (no boolean).
   - `boolean` compara contra boolean.
   - `object` requiere dict para `has_property`/`not_has_property`.
   - `array` requiere list para operadores de longitud/vacío.

4. Errores de tipo:
   - Deben indicar variable, tipo esperado, tipo recibido y operador.

---

## Enrutamiento True/False (impacto de motor)

Actualmente el motor usa nodos por `id` y no discrimina `source_output` en runtime. Para soportar IF correctamente se propone:

1. Extender resolución de inputs en `app/codegen/generator.py` para considerar `edge.source_output`.
2. Introducir estructura intermedia por nodo y por handle, por ejemplo:

```python
_node_outputs[node_id] = {
    "output_1": [...],
    "true": [...],
    "false": [...]
}
```

3. Para nodos existentes (una salida), seguir usando `output_1` para compatibilidad.
4. Para `if`, poblar únicamente `true` y `false`.
5. Al armar `_items` de un nodo downstream, tomar items desde el handle de salida especificado en cada edge entrante.

Beneficio: no rompe workflows actuales y habilita branching condicional real por item.

---

## Backend — cambios requeridos

## 1) Nuevo archivo

- `app/nodes/if_node.py` (clase `IfNode`)

## 2) Validación (`validate()`)

Validar:

- `input` obligatorio, patrón `^\$\{[A-Za-z_][A-Za-z0-9_]*\}$`
- `data_type` en `string|number|boolean|object|array`
- `operator` válido para `data_type`
- `compare_value` requerido o no según operador
  - requerido: la mayoría binarios
  - opcional/no usado: `is_true`, `is_false`, `is_empty`, `is_not_empty`, `exists`, `not_exists`

Mensajes sugeridos:

- `if: input must be a variable placeholder like ${MY_VAR}`
- `if: operator 'X' is not valid for type 'Y'`
- `if: compare_value is required for operator 'X'`

## 3) Generación (`to_code()`)

Generar evaluación por `_item` y construir dos listas:

- `_items_true`
- `_items_false`

Por cada item:

1. Resolver `input`.
2. Resolver `compare_value` si aplica.
3. Validar tipo del valor evaluado.
4. Ejecutar operador.
5. Append a lista `true` o `false`.

Salida del nodo propuesta en runtime:

```python
_node_branch_outputs = {
    "true": _items_true,
    "false": _items_false,
}
```

## 4) Registro

- `app/codegen/generator.py`
  - importar `IfNode`
  - agregar a `NODE_REGISTRY`

## 5) Ajustes de generador (clave)

Modificar `_emit_waves()` para:

- Construir `incoming_map` con `(source_node_id, source_output)` en lugar de solo `source_node_id`.
- Resolver entradas por handle correcto.
- Soportar retorno de nodo en forma:
  - lista (legacy)
  - dict por handle (nuevo)

Regla de compatibilidad:

- Si nodo retorna lista, tratarla como `output_1`.

---

## Frontend — cambios requeridos

## 1) Nuevo nodo React

- `frontend/src/nodes/IfNode.jsx`

Canvas:

- 1 input (`input_1`)
- 2 outputs (`true`, `false`)
- Label sugerido: `IF`

PropsForm:

- Campo `Variable a evaluar` (placeholder `${VARIABLE}`)
- Select `Tipo de dato`
- Select `Condición` (filtrado por tipo)
- Campo `Valor de comparación` (se oculta/deshabilita para operadores unarios)

## 2) Registro

- `frontend/src/nodes/index.js`
  - `nodeTypes.if`
  - `NODE_META.if`
  - `defaultConfig`

## 3) Base visual para múltiples salidas

Como `BaseNode` hoy soporta solo una salida (`output_1`), para `IfNode` se recomienda:

- implementar handles directamente en `IfNode.jsx` (similar a `MergeNode`), o
- extender `BaseNode` para aceptar arreglo de handles de salida.

## 4) Persistencia de edges

No requiere cambio de modelo: ya existe `source_output` en DB/API.

---

## Modelo de datos del nodo IF

```json
{
  "input": "${score}",
  "data_type": "number",
  "operator": "greater_or_equal",
  "compare_value": "70"
}
```

Ejemplos adicionales:

```json
{
  "input": "${user}",
  "data_type": "object",
  "operator": "has_property",
  "compare_value": "email"
}
```

```json
{
  "input": "${items}",
  "data_type": "array",
  "operator": "length_greater_than",
  "compare_value": "${min_items}"
}
```

---

## Estrategia de errores

Se propone **fail-fast por nodo** (alineado con nodos internos del motor):

- Si el nodo IF detecta placeholder faltante o incompatibilidad de tipo, lanza `ValueError` con contexto.
- El mensaje debe incluir operador y variable para diagnóstico rápido.

Mensajes sugeridos:

- `if: missing variable 'score' in input item`
- `if: incompatible types for operator 'greater_than' (left=string, right=number)`
- `if: operator 'has_property' requires object input, got list`

---

## Casos de prueba propuestos

## String

1. `equals` true/false.
2. `contains` y `not_contains`.
3. `is_empty` y `is_not_empty`.

## Number

4. `greater_than`, `less_or_equal`.
5. `compare_value` como `${threshold}` numérico.
6. Error por comparar número con string no parseable.

## Boolean

7. `is_true` y `is_false`.
8. Error con valor no boolean (`"yes"`).

## Object

9. `exists` / `not_exists` con `None` y dict.
10. `has_property` con propiedad presente/ausente.
11. Error cuando input no es object.

## Array

12. `is_empty` / `is_not_empty`.
13. `length_equals` / `length_greater_than`.
14. Error cuando input no es array.

## Routing

15. Grafo `IF -> rama true` y `IF -> rama false` verifica separación de items.
16. Compatibilidad: nodos no-IF siguen funcionando con `output_1`.

---

## Riesgos y mitigaciones

1. **Riesgo:** El generador actual no enruta por handle de salida.
   - **Mitigación:** introducir adaptación backward-compatible `list -> output_1` y `dict -> handles`.

2. **Riesgo:** Ambigüedad de conversiones (literal vs `${VAR}`).
   - **Mitigación:** reglas explícitas de resolución por tipo y operadores unarios/binarios.

3. **Riesgo:** UX confusa si se muestran operadores inválidos.
   - **Mitigación:** filtrar operador según `data_type` y limpiar operador al cambiar tipo.

---

## Archivos a modificar

- Backend:
  - `app/nodes/if_node.py` (nuevo)
  - `app/codegen/generator.py`

- Frontend:
  - `frontend/src/nodes/IfNode.jsx` (nuevo)
  - `frontend/src/nodes/index.js`

- Documentación (al cerrar implementación):
  - `README.md`
  - `_docs/CHECKLIST.md`

---

## Verificación recomendada (cuando se implemente)

Backend:

```bash
python -c "from app.main import app; print('OK')"
python -m py_compile app/nodes/if_node.py app/codegen/generator.py
```

Frontend:

```bash
cd frontend && npm run build
```

Smoke de validación de grafo (ejemplo conceptual):

```bash
python -c "from app.codegen.generator import validate_graph; print('pending if-node smoke')"
```

---

## Criterio de aceptación

1. Existe nodo `IF` configurable con variable, tipo, condición y valor de comparación.
2. Solo se muestran operadores válidos para el tipo seleccionado.
3. `${VARIABLE}` se resuelve correctamente en `input` y `compare_value`.
4. Tipos incompatibles generan error descriptivo.
5. El nodo enruta items en dos salidas reales: `true` y `false`.
6. Flujos existentes (nodos de una salida) siguen funcionando sin migración.
