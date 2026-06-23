# Plan de Implementacion - Nodo `map`

## Estado

Documento de planificacion. **No contiene implementacion**.

## Objetivo

Agregar un nuevo nodo `map` para transformar el valor de una variable de entrada en una nueva variable de salida, aplicando reglas condicionales de mapeo.

El nodo debe permitir:

- Definir el nombre de la variable nueva (`output_key`).
- Seleccionar la variable de entrada (`input_key` o expresion de entrada), soportando origen:
  - variable local
  - secreto
  - global
- Definir el tipo de dato de entrada para evaluar condiciones (similar al nodo `if`).
- Registrar multiples opciones de mapeo por condicion.
- Configurar el valor de salida por regla usando origen:
  - literal
  - variable
  - secreto
  - global

## Alcance

Incluye:

- Nodo backend + frontend (`map`).
- Formulario con lista dinamica de reglas de mapeo condicional.
- Selector de tipo de dato de entrada y operadores compatibles por tipo (similar a `if`).
- Soporte para tipos de valor de salida: literal, variable, secreto, global.
- Registro del nodo en `NODE_REGISTRY` y `NODE_META`.
- Validaciones de configuracion y errores claros en runtime.

No incluye (esta fase):

- Expresiones booleanas complejas (AND/OR anidado arbitrario).
- Editor visual avanzado de reglas.
- Mapeo por rangos numericos complejos con prioridad automatica.

## Reglas Funcionales

### 1) Estructura general del nodo

Configuracion propuesta:

```json
{
  "output_key": "status_label",
  "input_source": "${status_code}",
  "input_value_mode": "variable",
  "input_data_type": "number",
  "rules": [
    {
      "operator": "equals",
      "compare_value": "200",
      "value_mode": "literal",
      "mapped_value": "ok"
    },
    {
      "operator": "equals",
      "compare_value": "401",
      "value_mode": "secret",
      "mapped_value": "API_AUTH_ERROR"
    }
  ],
  "default": {
    "value_mode": "global",
    "mapped_value": "FALLBACK_STATUS"
  },
  "include_other_input_fields": true
}
```

### 2) Operadores de condicion

Los operadores deben ajustarse al `input_data_type`, siguiendo una logica equivalente al nodo `if`.

Catalogo inicial sugerido:

- Para `string`: `equals`, `not_equals`, `contains`, `starts_with`, `ends_with`, `is_empty`, `is_not_empty`
- Para `number`: `equals`, `not_equals`, `greater_than`, `greater_or_equal`, `less_than`, `less_or_equal`
- Para `boolean`: `is_true`, `is_false`, `equals`, `not_equals`

Regla de evaluacion:

- Se procesan en orden.
- La primera regla que cumple condicion define el valor final.
- Si ninguna cumple, se usa `default` cuando exista.
- Si no hay `default`, se retorna error explicito.

### 3) Modos de valor de salida (`value_mode`)

Cada regla y el `default` deben soportar:

- `literal`: usa `mapped_value` tal cual.
- `variable`: interpreta `mapped_value` como nombre de variable local (`${VAR}`).
- `secret`: interpreta `mapped_value` como nombre de secreto (`#{SECRET}`).
- `global`: interpreta `mapped_value` como nombre de variable global (`@{VAR}`).

### 4) Variable de entrada

`input_source` debe aceptar al menos:

- `${VAR_LOCAL}`
- `@{VAR_GLOBAL}`
- `#{SECRET_NAME}`

Se agrega `input_value_mode` para explicitar origen de la entrada:

- `variable` (local)
- `secret`
- `global`

Se agrega `input_data_type` para normalizar comparaciones (como en `if`):

- `string`
- `number`
- `boolean`

El backend debe convertir/coaccionar el valor de entrada al tipo indicado antes de evaluar reglas.

## Diseno Backend

### 1) Nuevo nodo

Crear archivo:

- `app/nodes/map.py`

Responsabilidades:

- `validate()`:
  - `output_key` obligatorio y valido.
  - `input_source` obligatorio.
  - `input_value_mode` obligatorio y valido (`variable|secret|global`).
  - `input_data_type` obligatorio y valido (`string|number|boolean`).
  - `rules` debe ser lista no vacia.
  - cada regla debe incluir `operator`, `compare_value`, `value_mode`, `mapped_value`.
  - validar operadores permitidos por tipo de dato de entrada (paridad con `if`).
  - validar `value_mode` permitido (`literal|variable|secret|global`).
- `to_code()`:
  - resolver valor de entrada segun `input_value_mode`.
  - convertir entrada a `input_data_type` antes de comparar.
  - convertir `compare_value` al tipo requerido cuando aplique.
  - evaluar reglas en orden.
  - resolver `mapped_value` segun `value_mode`.
  - escribir resultado en `_out[output_key]`.
  - errores contextuales claros cuando falten variable/secreto/global.

### 2) Resolucion de origenes

Para `value_mode`:

- `literal`: usar string/valor directamente.
- `variable`: resolver con helpers de `${...}` del runtime.
- `secret`: resolver con store de secretos `#{...}`.
- `global`: resolver con store global `@{...}`.

### 3) Registro backend

Actualizar:

- `app/codegen/generator.py` para agregar `MapNode` en `NODE_REGISTRY`.

## Diseno Frontend

### 1) Componente del nodo

Crear:

- `frontend/src/nodes/MapNode.jsx`

Con:

- Vista compacta en canvas (muestra `input_source`, `output_key`, cantidad de reglas).
- Formulario `MapPropsForm`.

### 2) Formulario de propiedades

Campos principales:

- `output_key` (variable nueva).
- `input_value_mode` (variable local, secreto, global).
- `input_source` (nombre/referencia de la variable de entrada segun el modo).
- `input_data_type` (`string`, `number`, `boolean`).
- Lista dinamica de reglas `rules`.
- Bloque `default` opcional.

Por cada regla:

- selector `operator` filtrado segun `input_data_type` (comportamiento similar a `if`).
- input `compare_value`.
- selector `value_mode` con opciones:
  - `literal`
  - `variable`
  - `secret`
  - `global`
- input `mapped_value`.
- boton eliminar regla.

Acciones:

- boton `+ Add rule`.
- orden de reglas editable (si no se implementa reorder, documentar evaluacion por orden actual).

### 3) Registro frontend

Actualizar:

- `frontend/src/nodes/index.js`

Agregar:

- `nodeTypes.map`
- `NODE_META.map` con label, descripcion, `defaultConfig`, `io` y `PropsForm`.

## Configuracion Inicial Sugerida

```json
{
  "output_key": "segment",
  "input_source": "${country}",
  "input_value_mode": "variable",
  "input_data_type": "string",
  "rules": [
    {
      "operator": "equals",
      "compare_value": "MX",
      "value_mode": "literal",
      "mapped_value": "latam"
    }
  ],
  "default": {
    "value_mode": "global",
    "mapped_value": "DEFAULT_SEGMENT"
  },
  "include_other_input_fields": true
}
```

## Criterios de Aceptacion

1. Existe nodo `map` visible en el editor.
2. Permite definir variable nueva (`output_key`) y variable de entrada con modo `variable|secret|global`.
3. Permite definir `input_data_type` y ajustar operadores de condicion de forma equivalente al nodo `if`.
4. Permite registrar multiples reglas condicionales de mapeo.
5. Cada regla soporta `value_mode`: `literal`, `variable`, `secret`, `global`.
6. El nodo evalua reglas en orden y aplica la primera coincidencia.
7. Soporta valor por defecto cuando no hay coincidencias.
8. El resultado queda disponible para nodos siguientes en `_out[output_key]`.

## Riesgos y Mitigaciones

- Riesgo: ambiguedad entre nombres de variable y templates.
  - Mitigacion: placeholders claros en UI (`${VAR}`, `#{SECRET}`, `@{GLOBAL}`).
- Riesgo: conversion de tipos invalida entre entrada y `compare_value`.
  - Mitigacion: coercion explicita por `input_data_type` y mensajes de error por regla.
- Riesgo: reglas superpuestas generan resultados inesperados.
  - Mitigacion: documentar prioridad por orden y mostrar indice de regla en UI.
- Riesgo: ausencia de `default` en escenarios no cubiertos.
  - Mitigacion: validacion opcional para exigir `default` o advertencia en UI.

## Plan por Fases

### Fase A - Backend base

1. Crear `app/nodes/map.py` con `validate()` y `to_code()`.
2. Registrar `MapNode` en `NODE_REGISTRY`.

### Fase B - Frontend

1. Crear `frontend/src/nodes/MapNode.jsx` y `MapPropsForm`.
2. Registrar nodo en `frontend/src/nodes/index.js`.

### Fase C - Integracion

1. Verificar guardado/carga de `rules` y `default`.
2. Verificar mapeo con los 4 modos (`literal`, `variable`, `secret`, `global`).
3. Verificar errores claros en faltantes de variable/secreto/global.

### Fase D - Verificacion rapida

1. `python -c "from app.main import app; print('OK')"`
2. `python -m py_compile app/main.py app/codegen/generator.py app/nodes/map.py`
3. `cd frontend && npm run lint -- src/nodes/MapNode.jsx src/nodes/index.js`

## Archivos Objetivo

- `app/nodes/map.py`
- `app/codegen/generator.py`
- `frontend/src/nodes/MapNode.jsx`
- `frontend/src/nodes/index.js`
- `README.md` (seccion de ejemplos de mapeo, si aplica)
