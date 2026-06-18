# Plan de Implementacion - Nodo `calculator`

## Estado

Documento de planificacion. **No contiene implementacion**.

## Objetivo

Agregar un nuevo nodo llamado `calculator` para ejecutar operaciones matematicas sobre valores literales o referencias a variables del flujo.

Debe soportar estas operaciones:

- `sum`
- `subtract`
- `multiply`
- `divide`
- `abs`
- `max`
- `min`
- `floor`
- `ceil`
- `x2`

## Alcance

Incluye:

- Nodo backend + frontend (canvas + formulario de propiedades).
- Selector de operacion por cada calculo.
- Inputs para operandos que acepten literal, `${VAR_NAME}` o `#{SECRET_NAME}`.
- Campo para definir nombre de variable de salida.
- Soporte de **multiples calculos** dentro del mismo nodo (patron similar a `set_variables`).
- Registro en `NODE_REGISTRY` y `NODE_META`.

No incluye (esta fase):

- Expresiones compuestas libres (ej. `a + b * c - d`).
- Mas de 2 operandos en operaciones binarias.
- Funciones matematicas fuera del listado requerido.

## Reglas Funcionales

### 1) Estructura por item de calculo

Cada item de calculo dentro de `config.calculations` tendra esta forma propuesta:

```json
{
  "output_key": "total",
  "operation": "sum",
  "left": "${price}",
  "right": "${tax}",
  "value_mode_left": "template",
  "value_mode_right": "template"
}
```

Notas:

- `output_key`: nombre de variable donde se guarda el resultado.
- `operation`: operacion seleccionada.
- `left` y `right`: operandos en formato string para permitir literal y placeholders.
- En operaciones unarias, `right` se ignora.

### 2) Restriccion de operandos

- Operaciones binarias (`sum`, `subtract`, `multiply`, `divide`, `max`, `min`) usan **2 operandos**.
- Operaciones unarias (`abs`, `floor`, `ceil`, `x2`) usan **1 operando** (`left`).
- El nodo no debe permitir operaciones con 3 o mas operandos.

### 3) Placeholders permitidos

Cada operando debe aceptar:

- Literal numerico (`10`, `3.14`, `-5`).
- Variable normal `${VAR_NAME}`.
- Secreto `#{SECRET_NAME}`.

## Diseno Backend

### 1) Nuevo nodo

Crear archivo:

- `app/nodes/calculator.py`

Responsabilidades:

- `validate()`
  - `calculations` debe ser lista.
  - cada item debe tener `output_key` valido (identificador python).
  - `operation` debe pertenecer al catalogo permitido.
  - validar cantidad de operandos segun tipo de operacion (binaria/unaria).
  - para `divide`, validar divisor no cero en tiempo de ejecucion (no solo parseo estatico).
- `to_code()`
  - resolver placeholders `${...}` y `#{...}`.
  - convertir operandos a numero (`int`/`float`) con errores claros.
  - ejecutar la operacion seleccionada.
  - guardar resultado en `_out[output_key]`.

### 2) Tabla de operaciones

Propuesta de mapeo:

- `sum`: `a + b`
- `subtract`: `a - b`
- `multiply`: `a * b`
- `divide`: `a / b` (error si `b == 0`)
- `abs`: `abs(a)`
- `max`: `max(a, b)`
- `min`: `min(a, b)`
- `floor`: `math.floor(a)`
- `ceil`: `math.ceil(a)`
- `x2`: `a * 2`

`math` debe estar disponible en el codigo generado cuando aplique (`floor`/`ceil`).

### 3) Registro

Actualizar:

- `app/codegen/generator.py` para registrar `CalculatorNode` en `NODE_REGISTRY`.

## Diseno Frontend

### 1) Componente de nodo

Crear:

- `frontend/src/nodes/CalculatorNode.jsx`

Con:

- Card de canvas mostrando cantidad de calculos configurados.
- `CalculatorPropsForm` con lista dinamica de calculos (similar a `SetVariablesPropsForm`).

### 2) Formulario por item

Cada bloque de calculo debe incluir:

- input `output_key` (nombre de variable de salida).
- selector `operation`.
- input `left` (valor/variable/secreto).
- input `right` (solo visible/habilitado en operaciones binarias).
- boton para eliminar item.

Debe existir boton `+ Add calculation` para agregar multiples items.

### 3) UX y ayudas

- Placeholder sugerido en operandos: `10`, `${price}`, `#{API_LIMIT}`.
- Mensaje breve de ayuda: "Acepta literales numericos, ${VAR} o #{SECRET}".
- Mantener estilo y patrones de nodos actuales (shadcn + estructura existente).

### 4) Registro frontend

Actualizar:

- `frontend/src/nodes/index.js`

Agregar:

- `nodeTypes.calculator`
- `NODE_META.calculator` con `defaultConfig`, label, io y `PropsForm`.

## Configuracion Propuesta

```json
{
  "calculations": [
    {
      "output_key": "subtotal",
      "operation": "sum",
      "left": "${price}",
      "right": "${shipping}"
    },
    {
      "output_key": "rounded_subtotal",
      "operation": "floor",
      "left": "${subtotal}",
      "right": ""
    }
  ],
  "include_other_input_fields": true
}
```

## Criterios de Aceptacion

1. Existe nodo `calculator` disponible en el editor.
2. Permite agregar multiples calculos en un mismo nodo.
3. Cada calculo tiene selector de operacion y nombre de variable de salida.
4. Operandos aceptan valor literal, `${VAR}` y `#{SECRET}`.
5. Operaciones binarias usan 2 operandos y unarias 1 operando.
6. El resultado de cada calculo queda disponible para nodos siguientes en `_out[output_key]`.
7. `divide` falla con error claro cuando el divisor es cero.

## Riesgos y Mitigaciones

- Riesgo: ambiguedad de parseo numerico (string no numerico).
  - Mitigacion: validacion y mensajes de error precisos por item.
- Riesgo: placeholders faltantes en runtime.
  - Mitigacion: reutilizar errores contextuales existentes para variable/secreto faltante.
- Riesgo: configuraciones grandes con muchos calculos.
  - Mitigacion: UI por bloques simples y boton de agregar/quitar como `set_variables`.

## Plan por Fases

### Fase A - Backend base

1. Crear `app/nodes/calculator.py` con validaciones y generacion de codigo.
2. Registrar nodo en `NODE_REGISTRY`.

### Fase B - Frontend

1. Crear `frontend/src/nodes/CalculatorNode.jsx`.
2. Registrar nodo en `frontend/src/nodes/index.js`.

### Fase C - Integracion

1. Verificar guardado/carga de configuracion con multiples calculos.
2. Verificar operaciones unarias y binarias con literales y placeholders.
3. Validar errores controlados (division por cero, variable faltante, valor invalido).
