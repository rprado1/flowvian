# PLANNING2 - Nodo Format Date

## 1) Objetivo

Implementar un nuevo nodo `format_date` para transformar una fecha del flujo a un formato de salida configurable.

El nodo debe permitir:

- seleccionar la variable de entrada con placeholder `${VARIABLE}`,
- elegir un formato de salida (incluyendo `Unix Ms Timestamp`),
- definir el nombre de la variable de salida,
- opcionalmente conservar los campos de entrada (`Include Other Input Fields`).

---

## 2) Alcance funcional

### Incluido

- Nuevo nodo backend `format_date`.
- Soporte de multiples formatos de fecha predefinidos.
- Opcion `Unix Ms Timestamp`.
- Configuracion de `input`, `format` y `output_var`.
- Opcion `include_other_input_fields`.
- Integracion completa con validate/preview/run/build.
- Nodo y formulario en frontend con selector de formato.

### No incluido (por ahora)

- Timezone personalizada por nodo (usar UTC/base runtime actual).
- Parseo de fechas con formato de entrada personalizado por usuario.
- Localizacion avanzada (idioma/locale para nombres de mes, etc.).

---

## 3) Semantica de ejecucion

Para cada `_item`:

1. Resolver `input` (placeholder `${VARIABLE}`) para obtener valor fecha.
2. Convertir el valor a `datetime` valido:
   - aceptar `datetime`,
   - aceptar string ISO 8601 (incluyendo sufijo `Z`),
   - aceptar timestamp numerico si se define en reglas (segundos o ms).
3. Aplicar formato seleccionado.
4. Escribir resultado en `output_var`.
5. Si `include_other_input_fields` es true, mezclar con `_item`.

Formato especial:

- `unix_ms_timestamp`: salida numerica en milisegundos desde epoch UTC.

---

## 4) Contrato de configuracion propuesto

Config base:

```json
{
  "input": "${current_date_utc}",
  "format": "iso_8601",
  "output_var": "formatted_date",
  "include_other_input_fields": false
}
```

Reglas:

- `input`: requerido, debe ser placeholder exacto `${VARIABLE}`.
- `format`: requerido, valor dentro del catalogo permitido.
- `output_var`: requerido, identificador valido.
- `include_other_input_fields`: boolean, default `false`.

Catalogo inicial de formatos sugeridos:

- `iso_8601` -> `2026-06-15T17:00:00Z`
- `date_yyyy_mm_dd` -> `2026-06-15`
- `datetime_yyyy_mm_dd_hh_mm_ss` -> `2026-06-15 17:00:00`
- `time_hh_mm_ss` -> `17:00:00`
- `unix_timestamp` -> `1718461200`
- `unix_ms_timestamp` -> `1718461200000`

---

## 5) Cambios backend

## 5.1 Nuevo nodo

Crear `app/nodes/format_date.py` con `FormatDateNode(BaseNode)`.

### validate()

- validar placeholder `input`.
- validar `format` en lista permitida.
- validar `output_var` no vacio e identificador valido.
- validar `include_other_input_fields` boolean.

### to_code()

- usar loop por item (`_emit_item_loop`) para respetar modelo N items.
- parsear fecha de entrada con reglas robustas (ISO/Z/datetime/timestamp).
- formatear segun `format` seleccionado.
- setear `_out[output_var]`.

Errores sugeridos:

- `format_date: input must be a variable placeholder like ${MY_DATE}`
- `format_date: missing variable 'MY_DATE' in input item`
- `format_date: unsupported format '...'`
- `format_date: cannot parse input date for variable 'MY_DATE'`

## 5.2 Registro

Actualizar `app/codegen/generator.py`:

- importar `FormatDateNode`.
- registrar en `NODE_REGISTRY`.

---

## 6) Cambios frontend

## 6.1 Nodo visual

Crear `frontend/src/nodes/FormatDateNode.jsx`:

- 1 entrada, 1 salida.
- resumen visual con `input` y formato elegido.

## 6.2 PropsForm

Campos:

1. `Input variable` (text) con placeholder `${VARIABLE}`.
2. `Output format` (select) con opciones del catalogo.
3. `Output variable` (text).
4. `Include Other Input Fields` (checkbox).

## 6.3 Registro en catalogo

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.format_date = FormatDateNode`.
- `NODE_META.format_date` con defaults y `PropsForm`.

## 6.4 Selector de nodos

- Incluir en categoria `Date and Time` del sidebar.

---

## 7) Pruebas sugeridas

## Backend

1. Input ISO -> `iso_8601` correcto.
2. Input ISO -> `date_yyyy_mm_dd` correcto.
3. Input ISO -> `unix_ms_timestamp` correcto.
4. Input variable faltante -> error claro.
5. Input invalido -> error claro de parseo.
6. `include_other_input_fields=true` conserva contexto.

## Integracion

7. Flujo `get_current_date_utc -> format_date -> set_variables` funciona.
8. `preview`, `run` y `build` sin regresiones.

## Frontend

9. Props del nodo persisten tras guardar/cargar.
10. Selector muestra todas las opciones de formato.

---

## 8) Riesgos y decisiones

### Riesgos

- Ambiguedad al parsear timestamps (segundos vs milisegundos).
- Diferencias por timezone si entrada no tiene zona explicita.

### Mitigaciones

- Definir regla explicita para timestamps (detectar por magnitud).
- Estandarizar conversion en UTC para salidas predecibles.

### Decisiones recomendadas

1. Trabajar internamente en UTC.
2. Soportar `unix_ms_timestamp` como formato requerido.
3. Mantener `include_other_input_fields=false` por defecto.

---

## 9) Resultado esperado

Contar con un nodo `format_date` configurable y consistente con el motor de items, capaz de transformar fechas del flujo a formatos comunes (incluyendo `Unix Ms Timestamp`) y exponerlas en una variable de salida definida por el usuario.
