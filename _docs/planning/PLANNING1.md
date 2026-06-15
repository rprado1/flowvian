# PLANNING1 — Set Variables con tipos (String, Number, Boolean)

## Objetivo

Extender el nodo `set_variables` para que cada variable pueda declararse con tipo explícito:

- `String`
- `Number`
- `Boolean`
- `Array`

El objetivo es que el valor en `_out` preserve el tipo definido por el usuario y no quede siempre como texto.

---

## Alcance funcional

## Comportamiento esperado

- Cada fila de variable en `Set Variables` tendrá:
  - `key`
  - `type` (`string | number | boolean | array`)
  - `value`
- El valor se convertirá según el tipo seleccionado:
  - `string`: siempre `str`
  - `number`: `int` o `float` según entrada
  - `boolean`: `true/false` (case-insensitive), también admitir `1/0`
  - `array`: JSON array válido (p.ej. `[1, "x", true]`)
- Se mantiene la opción existente `Include Other Input Fields`.

## Compatibilidad hacia atrás

- Flujos existentes sin campo `type` deben seguir funcionando.
- Regla de compatibilidad propuesta: si falta `type`, asumir `string`.

---

## Diseño técnico propuesto

## 1) Backend

### 1.1 `app/nodes/set_variables.py` — validación

Actualizar `validate()` para cada variable:

- `key` no vacía y válida (como hoy)
- `type` opcional, default `string`
- `type` debe pertenecer a `{string, number, boolean, array}`
- validar el `value` acorde al tipo:
  - `number`: debe parsear a número
  - `boolean`: debe ser uno de `true/false/1/0` (case-insensitive)
  - `array`: debe parsear como JSON y su raíz debe ser lista

Mensajes de error sugeridos:

- `set_variables: item {i} has invalid type '{type}'`
- `set_variables: item {i} value '{value}' is not a valid number`
- `set_variables: item {i} value '{value}' is not a valid boolean`
- `set_variables: item {i} value must be a valid JSON array`

### 1.2 `app/nodes/set_variables.py` — generación de código

Modificar `to_code()` para emitir tipos reales en `_out`:

- `string`:
  - `_out['k'] = 'valor'`
- `number`:
  - convertir a `int` si no hay decimal; si no, `float`
- `boolean`:
  - `_out['k'] = True/False`
- `array`:
  - parsear JSON array y emitir literal Python equivalente (lista)

Esto evita conversión en runtime y mantiene script generado simple y determinista.

---

## 2) Frontend

### 2.1 `frontend/src/nodes/SetVariablesNode.jsx`

Actualizar formulario para cada variable con:

- Input `key`
- Select `type` (`String`, `Number`, `Boolean`, `Array`)
- Input `value`

Default al agregar fila:

```js
{ key: '', type: 'string', value: '' }
```

### 2.2 UX de edición

- Si el usuario cambia tipo, mantener el texto de `value` y validar en backend.
- (Opcional recomendado) validación visual ligera en frontend para mejorar UX.

### 2.3 Canvas node (resumen)

- No requiere cambios funcionales.
- Opcional: mostrar conteo por tipo (`2 string, 1 number`).

---

## 3) Modelo de datos del nodo

## Nuevo esquema por variable

```json
{
  "variables": [
    { "key": "name", "type": "string", "value": "john" },
    { "key": "age", "type": "number", "value": "32" },
    { "key": "active", "type": "boolean", "value": "true" },
    { "key": "tags", "type": "array", "value": "[\"vip\", \"beta\"]" }
  ],
  "include_other_input_fields": false
}
```

Compatibilidad legacy:

```json
{ "key": "x", "value": "1" }
```

Se interpreta como `type = string`.

---

## 4) Reglas de conversión

## Number

- `int`: `^-?\d+$`
- `float`: `^-?\d+\.\d+$`
- Si parsea como entero exacto, generar `int`; si no, `float`.

## Boolean

Valores aceptados (case-insensitive):

- verdaderos: `true`, `1`
- falsos: `false`, `0`

Se generan como literales Python `True` / `False`.

## String

- Se guarda tal cual como cadena (`str(value)`).

## Array

- `value` debe ser JSON válido y su raíz una lista.
- Se permite contenido mixto JSON (`string`, `number`, `boolean`, `object`, `array`, `null`).
- El valor final en `_out` debe ser una lista Python.

---

## 5) Cambios de archivos

- Backend:
  - `app/nodes/set_variables.py`
- Frontend:
  - `frontend/src/nodes/SetVariablesNode.jsx`
- Documentación (si aplica al finalizar):
  - `README.md`
  - `_docs/CHECKLIST.md`

---

## 6) Verificación

## Backend

```bash
python -c "from app.main import app; print('OK')"
python -m py_compile app/nodes/set_variables.py app/codegen/generator.py
```

Smoke test rápido:

```bash
python -c "from app.codegen.generator import validate_graph; nodes=[{'id':'n1','type':'set_variables','label':'Set','config':{'variables':[{'key':'age','type':'number','value':'32'},{'key':'active','type':'boolean','value':'true'}]}}]; print(validate_graph(nodes, []))"
```

## Frontend

```bash
cd frontend && npm run build
```

## Funcional end-to-end

1. `Set Variables` con:
   - `name:string='john'`
   - `age:number='32'`
   - `active:boolean='true'`
   - `tags:array='["vip","beta"]'`
2. Ejecutar `Run`.
3. Confirmar en `items_out`:
   - `name` string
   - `age` number
   - `active` boolean
   - `tags` array/list

---

## 7) Riesgos y decisiones

- Riesgo: usuarios con datos legacy sin `type`.
  - Mitigación: fallback a `string`.
- Riesgo: confusión por entrada booleana libre.
  - Mitigación: mensajes de error claros + guía en placeholder.
- Decisión: en esta fase se agrega `array`, pero se mantiene fuera `object` y `null` como tipos explícitos.

---

## 8) Criterio de aceptación

- El nodo `Set Variables` permite elegir tipo por variable (`string/number/boolean/array`).
- El backend valida tipos y valores correctamente.
- El código generado preserva tipos reales en salida.
- Flujos antiguos continúan funcionando sin migración manual.
