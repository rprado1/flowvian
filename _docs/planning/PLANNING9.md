# PLANNING9 - Nodo Filter

## 1) Objetivo

Implementar un nuevo nodo `filter` similar al nodo `if`, pero con una sola salida.

Comportamiento esperado:

- El nodo evalua condiciones sobre cada item del flujo.
- Solo los items que cumplen la condicion pasan a la salida.
- Los items que no cumplen se descartan.

---

## 2) Alcance funcional

### Incluido

- Nuevo nodo backend: `filter`.
- Validacion de configuracion similar a `if` (tipos, operadores, placeholders, join AND/OR).
- Una sola salida en frontend/canvas.
- Formulario de propiedades reutilizando la experiencia del `if` (multi-condicion).
- Integracion completa con run/preview/build.

### No incluido (por ahora)

- Segunda salida para descartados.
- Modo "keep rejected" o salida de auditoria dedicada.
- UI avanzada de expresiones complejas (parens/grupos anidados).

---

## 3) Semantica de ejecucion

Para cada `_item` de entrada:

1. Evaluar condiciones configuradas (una o multiples).
2. Resolver placeholders tipo `${VARIABLE}` para input y compare_value.
3. Aplicar operador segun tipo (`string`, `number`, `boolean`, `object`, `array`).
4. Combinar resultados con `and/or`.
5. Si el resultado final es `true`, agregar `_item` a `_items_filtered`.
6. Si es `false`, no agregar item.

Resultado final del nodo:

- `_items = _items_filtered`
- Una sola salida (`output_1`).

Debug recomendado:

- Conteo de entrada/salida.
- Evaluaciones por item (similar a `if`), para trazabilidad en run panel.

---

## 4) Contrato de configuracion propuesto

Config base sugerida (alineada al `if`):

```json
{
  "input": "${value}",
  "data_type": "string",
  "operator": "equals",
  "compare_value": "",
  "conditions": [
    {
      "join": "and",
      "input": "${value}",
      "data_type": "string",
      "operator": "equals",
      "compare_value": ""
    }
  ]
}
```

Notas:

- Mantener compatibilidad con formato legacy (input/data_type/operator/compare_value).
- Preferir `conditions[]` como fuente principal.

---

## 5) Cambios backend

## 5.1 Nuevo nodo

Crear `app/nodes/filter.py` con `FilterNode(BaseNode)`.

### validate()

- Reutilizar reglas del `IfNode` para:
  - placeholder exacto `${VAR}` en `input`;
  - `data_type` valido;
  - operador valido por tipo;
  - `compare_value` requerido para operadores no unarios;
  - `join` valido en condiciones secundarias.

### to_code()

- Reutilizar logica de evaluacion tipada del `IfNode`.
- En lugar de `true/false branches`, generar una sola coleccion:
  - `_items_filtered = []`
  - si condicion final true -> append item
- Publicar `_node_debug` con metricas:
  - `items_in`
  - `items_out`
  - `filtered_out`

## 5.2 Registro del nodo

Actualizar `app/codegen/generator.py`:

- importar `FilterNode`.
- registrar `FilterNode.NODE_TYPE` en `NODE_REGISTRY`.

---

## 6) Cambios frontend

## 6.1 Componente del nodo

Crear `frontend/src/nodes/FilterNode.jsx`:

- 1 entrada (`input_1`), 1 salida (`output_1`).
- titulo + descripcion corta (ej. "Keep items matching conditions").

## 6.2 PropsForm

- Implementar `FilterPropsForm` muy similar a `IfPropsForm`:
  - multiples condiciones,
  - join AND/OR,
  - tipos de datos,
  - operadores por tipo,
  - compare value cuando aplica.

## 6.3 Registro en catalogo

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.filter = FilterNode`
- `NODE_META.filter` con:
  - `label`, `icon`, `description`
  - `inputs: 1`, `outputs: 1`
  - `defaultConfig`
  - `PropsForm: FilterPropsForm`

## 6.4 Sidebar / selector

- Verificar que aparezca en Node Selector por categoria adecuada (ej. `Logic`).

---

## 7) Pruebas sugeridas

## Backend (smoke)

1. String equals: filtra correctamente.
2. Number greater_than: conserva solo items esperados.
3. Boolean is_true/is_false.
4. Object has_property/not_has_property.
5. Array length comparators.
6. Multi-condicion AND/OR.
7. Variable faltante en input/compare -> error claro.

## Integracion

8. `set_variables -> filter -> ...` mantiene consistencia de items.
9. `run` muestra trazas y conteo de items filtrados.
10. `preview` y `build` sin regresiones.

## Frontend

11. Configuracion del nodo persiste tras guardar/cargar workflow.
12. El nodo permite conexion normal en canvas (1 salida).

---

## 8) Riesgos y decisiones

### Riesgos

- Duplicar mucha logica del `if` y dificultar mantenimiento.
- Inconsistencias en operadores entre `if` y `filter`.

### Mitigaciones

- Extraer helpers compartidos en backend/frontend cuando sea posible.
- Mantener tablas de operadores centralizadas.

### Decisiones propuestas

1. `filter` descarta items no coincidentes (sin salida secundaria).
2. Mantener formato de configuracion alineado al `if` para UX consistente.
3. Incluir `_node_debug` para observabilidad en ejecucion.

---

## 9) Resultado esperado

Contar con un nodo `filter` que permita reducir el flujo de items conservando solo los que cumplen condiciones, con UX y semantica consistentes con el nodo `if`, pero con una unica salida orientada a "items filtrados".
