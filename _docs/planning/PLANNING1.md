# PLANNING1 - Nodo Aggregate

## 1) Objetivo

Implementar el nodo `aggregate`, que realiza la operacion contraria a `split`:

- Toma N items del flujo de entrada.
- Los combina en un solo item de salida.
- Dentro de ese item, genera una lista con todos los items originales y sus campos.

---

## 2) Alcance funcional

### Incluido

- Nuevo nodo backend `aggregate`.
- Una entrada y una salida en frontend.
- Configuracion para nombre de campo de salida (lista agregada).
- Opcion para conservar campos de contexto (si aplica).
- Integracion completa con run/preview/build.

### No incluido (por ahora)

- Estrategias avanzadas de agregacion (sum, group by, distinct, etc.).
- Agregacion por ventanas o lotes parciales.
- Agregacion jerarquica por condiciones.

---

## 3) Semantica de ejecucion

Entrada:

- `_items` = lista de items (cada item es un objeto/dict).

Salida esperada:

- `_items` con exactamente 1 item.
- Ese item contiene una propiedad lista que debe ser definida en la configuracion (ej. `items`) con todos los items de entrada.

Ejemplo:

Entrada:

```json
[
  { "id": 1, "name": "A" },
  { "id": 2, "name": "B" }
]
```

Salida:

```json
[
  {
    "items": [
      { "id": 1, "name": "A" },
      { "id": 2, "name": "B" }
    ]
  }
]
```

---

## 4) Contrato de configuracion propuesto

Config minima:

```json
{
  "output_var": "items",
  "include_other_input_fields": false
}
```

Reglas:

- `output_var`:
  - requerido,
  - string no vacio,
  - nombre del campo donde se guardara la lista agregada.
- `include_other_input_fields`:
  - opcional,
  - boolean,
  - si `true`, toma como base el primer item para conservar contexto y agrega `output_var` encima.

---

## 5) Cambios backend

## 5.1 Nuevo nodo

Crear `app/nodes/aggregate.py` con `AggregateNode(BaseNode)`.

### validate()

- Validar `output_var` no vacio.
- Validar tipo booleano de `include_other_input_fields`.

### to_code()

- Construir `_aggregated_list = list(_items)`.
- Crear `_out = {output_var: _aggregated_list}`.
- Si `include_other_input_fields = true` y hay items, fusionar con el primer item.
- Reemplazar `_items` por lista de un solo item: `[_out]`.
- Exponer `_node_debug` con conteo `items_in` y `items_out`.

## 5.2 Registro

Actualizar `app/codegen/generator.py`:

- importar `AggregateNode`.
- registrar en `NODE_REGISTRY`.

---

## 6) Cambios frontend

## 6.1 Componente del nodo

Crear `frontend/src/nodes/AggregateNode.jsx`:

- 1 entrada (`input_1`).
- 1 salida (`output_1`).
- Descripcion: "Combine all items into one list".

## 6.2 PropsForm

Campos:

- `Output variable` (texto), default `items`.
- `Include Other Input Fields` (checkbox).

## 6.3 Registro en catalogo

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.aggregate = AggregateNode`.
- `NODE_META.aggregate` con `defaultConfig` y `PropsForm`.

## 6.4 Selector de nodos

- Incluir `aggregate` en categoria de datos (`Data`) en el sidebar.

---

## 7) Pruebas sugeridas

## Backend (smoke)

1. Con 3 items de entrada, salida tiene 1 item con lista de 3 elementos.
2. `output_var` personalizado funciona (`records`, `all_rows`, etc.).
3. `include_other_input_fields = true` conserva campos del primer item.
4. Entrada vacia produce 1 item con lista vacia o comportamiento definido (decidir y documentar).

## Integracion

5. Flujo `split -> aggregate` recompone estructura esperada.
6. `run`, `preview` y `build` sin regresiones.

## Frontend

7. Configuracion persiste tras guardar/cargar workflow.
8. Conexion en canvas funciona con entrada/salida unica.

---

## 8) Riesgos y decisiones

### Riesgos

- Ambiguedad sobre comportamiento cuando `_items` esta vacio.
- Conflicto de nombre si `output_var` ya existe en contexto base.

### Mitigaciones

- Definir explicitamente comportamiento para entrada vacia (recomendado: generar `[{output_var: []}]`).
- En merge de contexto, priorizar `output_var` final sobre campos existentes.

### Decisiones recomendadas

1. Mantener salida siempre como un solo item.
2. `output_var` default: `items`.
3. Default UX `include_other_input_fields = false` para evitar resultados inesperados.

---

## 9) Resultado esperado

Contar con un nodo `aggregate` que permita consolidar todos los items del flujo en una sola lista dentro de un unico item de salida, simplificando escenarios de post-procesamiento, respuesta final y serializacion de resultados.
