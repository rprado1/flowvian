# PLANNING2 — Set Variables: referencias `${variable}` + ajuste de layout

## Objetivo

Planificar dos mejoras para el nodo `set_variables`:

1. Permitir que el valor de cada `key` use referencias del flujo con sintaxis `${NOMBRE_VARIABLE}` (similar al comportamiento del nodo HTTP Request).
2. Cambiar el layout del formulario para que cada fila se muestre en líneas separadas:
   - `[Input key]`
   - `[Select type]`
   - `[Input value]`

**Nota:** este documento es solo planificación. No se implementa en esta etapa.

---

## Alcance funcional

## 1) Interpolación en Set Variables

Cada variable en `set_variables` podrá declarar `value` con placeholders `${...}`.

Ejemplos:

- `"Hola ${name}"` -> string interpolado
- `${age}` con tipo `number` -> toma valor del flujo y lo valida como número
- `${active}` con tipo `boolean` -> toma valor del flujo y lo valida como boolean
- `${tags}` con tipo `array` -> toma valor del flujo y lo valida como lista

Comportamiento esperado:

- Si el placeholder no existe en `_item`, marcar error por item con mensaje claro.
- Si existe pero no es compatible con el tipo declarado, marcar error por item.
- Mantener `include_other_input_fields` como hoy.

## 2) Layout del formulario

Actualmente cada fila se renderiza horizontalmente (`key | type | value`).
Se requiere render vertical por fila:

- línea 1: input `key`
- línea 2: select `type`
- línea 3: input `value`

Sin cambiar semántica de guardado ni estructura de datos del nodo.

---

## Diseño técnico propuesto

## Backend

Archivo principal:

- `app/nodes/set_variables.py`

### Cambios propuestos

1. Agregar helper de resolución de placeholders para `set_variables`:
   - Reutilizar lógica equivalente a `_resolve_template` y `fullmatch` de `${VAR}`.
2. Aplicar resolución en runtime dentro de `to_code()` por cada `_item`.
3. Separar dos etapas por variable:
   - resolver valor (`value` -> valor resultante)
   - convertir/validar según tipo (`string/number/boolean/array`)

### Estrategia por tipo con `${...}`

- `string`:
  - si contiene texto + placeholders, interpolar a string final.
- `number`:
  - si `value` es `${VAR}` exacto, usar valor original de `_item[VAR]` y parsear número.
  - si es texto interpolado, parsear número del string resultante.
- `boolean`:
  - misma lógica que number, con parseo boolean.
- `array`:
  - si es `${VAR}` exacto y variable ya es lista -> usarla.
  - si resulta string JSON -> parsear y exigir lista.

### Manejo de error recomendado

No romper toda la ejecución por un item inválido (alineado con robustez de nodos con integración externa).

Salida sugerida por item cuando falle resolución/conversión:

- `set_variables_error: "..."`
- mantener flujo del resto de items.

Alternativa (si se decide fail-fast): lanzar excepción con contexto del key e índice.

---

## Frontend

Archivo principal:

- `frontend/src/nodes/SetVariablesNode.jsx`

### Cambios de UI

1. Reestructurar cada fila de variable a layout vertical (`space-y-*`).
2. Mantener botón eliminar por fila, pero adaptado a formato en bloque.
3. Añadir ayuda contextual pequeña en `value`:
   - "Use `${variable}` para tomar datos del flujo"

### Cambios no funcionales

- No cambia el shape persistido de `config.variables`.
- No requiere cambios en `NODE_META`.

---

## Modelo de datos (sin cambios estructurales)

Se conserva:

```json
{
  "variables": [
    { "key": "customer_id", "type": "string", "value": "${CUSTOMER_ID}" },
    { "key": "amount", "type": "number", "value": "${TOTAL_AMOUNT}" },
    { "key": "enabled", "type": "boolean", "value": "${IS_ACTIVE}" },
    { "key": "tags", "type": "array", "value": "${TAGS}" }
  ],
  "include_other_input_fields": true
}
```

---

## Reglas de interpolación

Patrón:

- `${NOMBRE_VARIABLE}`

Reglas:

1. Placeholder exacto (`^\$\{...\}$`) permite conservar tipo original para `number/boolean/array`.
2. Placeholder embebido en texto produce string.
3. Variable inexistente -> error explícito por item.

---

## Casos de prueba propuestos

## Funcionales

1. `string` con texto + `${name}`.
2. `number` con `${age}` donde `age` es int.
3. `boolean` con `${active}` donde `active` es bool.
4. `array` con `${items}` donde `items` es lista.

## Errores

5. `${VARIABLE_INEXISTENTE}`.
6. `number` con `${name}` no numérico.
7. `boolean` con `${value}` inválido.
8. `array` con `${value}` no lista.

## UI

9. Cada fila renderiza key, type, value en líneas separadas.
10. Add/remove variable no rompe layout.

---

## Riesgos

- Ambigüedad entre placeholder exacto vs texto interpolado para tipos no-string.
- Comportamiento de error (fail-fast vs por-item) debe definirse para no romper expectativas.
- Cambios visuales pueden requerir ajuste CSS para mantener consistencia con nodos existentes.

---

## Preguntas abiertas

1. ¿Cuando falle una variable en un item, se descarta ese item o se propaga con campo de error?
2. ¿Se debe permitir múltiple placeholder en `number/boolean/array` o solo placeholder exacto?
3. ¿La interpolación debe soportar anidación avanzada o solo `${VAR}` plano?

---

## Criterio de aceptación (cuando se implemente)

- `set_variables` permite `${VARIABLE}` en `value` para todos los tipos soportados.
- La conversión por tipo funciona correctamente tras resolver placeholders.
- El formulario muestra cada campo en línea separada por variable.
- No se rompe compatibilidad con workflows existentes.
