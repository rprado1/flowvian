# PLANNING3 — Set Variables: seleccionar campos dentro de objetos de entrada

## Objetivo

Extender el nodo `set_variables` para que, cuando el input del flujo tenga objetos anidados (ej. `{"args": {"country": "EC"}}`), el usuario pueda mapear una variable desde una ruta interna del objeto (por ejemplo `args` o `args.country`).

Este documento define la propuesta funcional/técnica. **No implementar en esta etapa.**

---

## Requerimiento

Caso base solicitado:

- Input item: `{"args": {"country": "EC"}}`
- En `Set Variables`, al definir una variable, poder seleccionar un item interno del objeto (ej. `args`) para usarlo como valor.

Extensión recomendada:

- Soportar también rutas anidadas (`args.country`, `args.meta.code`, etc.).

---

## Alcance funcional

## Incluido

1. En cada variable de `Set Variables`, habilitar un modo de valor basado en **ruta de objeto del input**.
2. Resolver rutas sobre `_item` actual en runtime.
3. Compatibilidad con tipos existentes del nodo (`string`, `number`, `boolean`, `array`, `object`).
4. Mantener soporte de `${variable}` ya existente.

## No incluido (fase futura)

- Explorador visual profundo tipo tree-view de JSON completo.
- Autocompletado inteligente por esquema global del workflow.
- JSONPath completo con filtros (`$..`, `[?()]`, etc.).

---

## Diseño funcional propuesto

Para cada variable en `Set Variables`, agregar `value_mode`:

- `literal` (default actual)
- `template` (usa `${...}`)
- `path` (nuevo: toma valor por ruta del `_item`)

Campos por variable propuestos:

```json
{
  "key": "country",
  "type": "string",
  "value_mode": "path",
  "value": "args.country"
}
```

Notas:

- `value` se reutiliza para almacenar la ruta cuando `value_mode=path`.
- Para compatibilidad, si `value_mode` no existe:
  - si `value` contiene `${...}` -> tratar como `template`
  - si no -> `literal`

---

## Sintaxis de rutas

Propuesta mínima segura:

- Dot notation: `args.country`
- Acceso de índice de arrays: `items[0].name`

Ejemplos válidos:

- `args`
- `args.country`
- `payload.items[0].id`

Errores de ruta:

- si no existe la ruta -> error por item con mensaje claro
- si el tipo final no coincide con `type` -> error de conversión como hoy

---

## Backend — cambios requeridos

Archivo principal:

- `app/nodes/set_variables.py`

### Cambios

1. Agregar parser/resolvedor de ruta:
   - helper `_resolve_path(_item, path)`
   - soportar claves y `[...]` numéricos
2. Integrar `value_mode` en `to_code()`:
   - `literal`: comportamiento actual
   - `template`: comportamiento `${...}` actual
   - `path`: usar `_resolve_path` para obtener valor fuente
3. Mantener validación por `type` (number/boolean/array/object/string) sobre el valor resuelto.
4. En `validate()`:
   - validar que `value_mode` sea permitido
   - validar forma de path (regex básica), sin requerir conocer datos reales en diseño

### Mensajes de error sugeridos

- `set_variables: key '<k>' path '<p>' not found`
- `set_variables: key '<k>' invalid path syntax '<p>'`

---

## Frontend — cambios requeridos

Archivo principal:

- `frontend/src/nodes/SetVariablesNode.jsx`

### Cambios de UI por variable

Agregar selector `Value Source`:

- Literal
- Template (${...})
- Path (input object)

Render condicional de `value`:

- Literal: input normal
- Template: input con ayuda `${variable}`
- Path: input con placeholder `args.country` + ayuda

### UX recomendada

- Si hay `selectedNode` con `items_in` reciente (desde run traces), mostrar sugerencias de primer nivel (`args`, `payload`, etc.) para modo Path.
- No bloquear guardado si no hay sugerencias (permitir escritura manual).

---

## Modelo de datos actualizado

```json
{
  "variables": [
    { "key": "raw_args", "type": "object", "value_mode": "path", "value": "args" },
    { "key": "country", "type": "string", "value_mode": "path", "value": "args.country" },
    { "key": "msg", "type": "string", "value_mode": "template", "value": "Country: ${country}" }
  ],
  "include_other_input_fields": true
}
```

Compatibilidad legacy:

- variables sin `value_mode` siguen funcionando sin migración.

---

## Casos de prueba

## Funcionales

1. Input `{"args":{"country":"EC"}}`, path `args` -> salida object.
2. Input `{"args":{"country":"EC"}}`, path `args.country` -> salida string `EC`.
3. Input con array, path `items[0].id` -> salida correcta.

## Tipos

4. Path a número con type `number` -> ok.
5. Path a string con type `number` -> error de conversión.
6. Path a object con type `object` -> ok.
7. Path a object con type `array` -> error.

## Errores

8. Path inexistente -> error claro.
9. Sintaxis inválida (`args..country`, `items[x]`) -> error claro.

## Compatibilidad

10. Variables legacy (sin `value_mode`) siguen ejecutando igual.

---

## Riesgos

- Complejidad creciente en `set_variables.py` (ya tiene lógica de tipos + templates).
- Ambigüedad entre `template` y `path` si no se define un `value_mode` claro.
- UX: sin sugerencias automáticas, usuarios pueden cometer errores de ruta.

Mitigación:

- helpers pequeños y testeables en backend
- `value_mode` explícito en frontend
- mensajes de error precisos

---

## Preguntas abiertas

1. ¿Ruta debe soportar únicamente dot notation + índice numérico, o algo más avanzado?
2. ¿En error de path se descarta item o se aborta nodo completo?
3. ¿Queremos autocompletado básico de rutas desde el último `items_in` ejecutado?

---

## Criterio de aceptación

- El nodo `Set Variables` permite seleccionar valor desde ruta de objeto del input.
- Caso solicitado (`args`) funciona correctamente.
- También funciona en rutas anidadas simples (`args.country`).
- Se mantiene compatibilidad con `literal` y `${variable}` existentes.
