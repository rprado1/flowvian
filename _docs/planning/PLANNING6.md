# PLANNING6 - Nodo Split

## 1) Objetivo

Implementar un nodo `split` que reciba una variable en formato `${VARIABLE}` (de tipo array) y transforme cada elemento del array en un item independiente dentro del flujo.

El nodo debe permitir la opcion `Include Other Input Fields` para decidir si cada item nuevo conserva o no los demas campos del item original.

---

## 2) Alcance funcional

### Incluido

- Nodo nuevo: `split`.
- Input: expresion `${VARIABLE}` obligatoria.
- Validacion de que la variable exista y sea `array`.
- Salida: un item por cada elemento del array.
- Opcion `include_other_input_fields`.
- Integracion con run/preview/build sin cambios de contrato externo.

### No incluido (por ahora)

- Split por string (delimiter) o por object keys.
- Opciones avanzadas (chunk size, max items, flatten profundo).
- Modo tolerant (ignorar errores de tipo y continuar).

---

## 3) Semantica de ejecucion

Para cada `_item` entrante:

1. Resolver nombre de variable desde `${VARIABLE}`.
2. Obtener `_arr = _item[VARIABLE]`.
3. Validar que `_arr` sea lista (`list`).
4. Crear nuevos items:
   - Si `include_other_input_fields = false`:
     - salida por elemento: `{ output_var: element }` o `{ variable_name: element }` segun diseno elegido.
   - Si `include_other_input_fields = true`:
     - salida por elemento: `{ **_item, variable_name: element }`.

Resultado final del nodo: concatenacion de todos los nuevos items generados por cada item de entrada.

Notas de consistencia:

- El orden de salida debe preservar el orden original del array.
- Si el array esta vacio, ese item de entrada no produce salidas.

---

## 4) Contrato de configuracion del nodo

Config minima propuesta:

```json
{
  "input": "${items}",
  "include_other_input_fields": true
}
```

Reglas:

- `input` requerido, string, placeholder exacto `${NAME}`.
- `include_other_input_fields` opcional, default `false` o `true` (definir en metadata; recomendacion abajo).

Recomendacion UX:

- Default `include_other_input_fields = true` para evitar perdida inesperada de contexto.

---

## 5) Cambios backend

## 5.1 Nuevo nodo

Crear `app/nodes/split.py` con `SplitNode(BaseNode)`.

### validate()

- Verificar `input` no vacio.
- Verificar placeholder exacto `${VARIABLE}`.
- Validar tipo de `include_other_input_fields` (bool).

### to_code()

Generar loop item-by-item que:

- valida presencia de variable en `_item`.
- valida tipo `list`.
- itera cada elemento y agrega `_out` a `_next_items`.
- respeta `include_other_input_fields`.

Errores sugeridos:

- `split: input must be a variable placeholder like ${MY_ARRAY}`
- `split: missing variable 'MY_ARRAY' in input item`
- `split: variable 'MY_ARRAY' must be an array, got <type>`

## 5.2 Registro

Actualizar `app/codegen/generator.py`:

- import `SplitNode`.
- agregar `SplitNode.NODE_TYPE` a `NODE_REGISTRY`.

No se requieren cambios de arquitectura en waves/paralelismo.

---

## 6) Cambios frontend

## 6.1 Componente de nodo

Crear `frontend/src/nodes/SplitNode.jsx`:

- card con icono sugerido `✂️`.
- `inputs: 1`, `outputs: 1`.
- subtitulo: `Split array into items`.

## 6.2 PropsForm

Campos:

- `Variable to split` (input text) con placeholder `${ARRAY_VAR}`.
- checkbox `Include Other Input Fields`.

Texto de ayuda:

- `Variable must resolve to an array for each input item.`

## 6.3 Registro en catalogo

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.split = SplitNode`
- `NODE_META.split` con `defaultConfig`.

Default config sugerido:

```json
{
  "input": "${items}",
  "include_other_input_fields": true
}
```

---

## 7) Compatibilidad y contrato de datos

- Mantener el modelo de items como array de objetos.
- No cambiar formato de `final_output` ni trazas globales.
- El nodo se comporta como transformador de cardinalidad (1 -> N por item).

---

## 8) Casos de prueba sugeridos

## Unit/smoke backend

1. Input valido `${arr}` con `arr = [1,2,3]` produce 3 items.
2. `include_other_input_fields = true` conserva campos originales.
3. `include_other_input_fields = false` solo incluye campo split.
4. `arr = []` produce 0 items para ese item.
5. Variable ausente -> error claro.
6. Variable no array (string/object/null) -> error claro.

## Integracion

7. `set_variables -> split -> merge` mantiene orden esperado.
8. Run instrumentado muestra `items_in` y `items_out` correctos.
9. Build/preview generan script valido sin regresiones.

---

## 9) Riesgos y decisiones abiertas

## Riesgos

- Ambiguedad del nombre del campo de salida cuando se splittea `${arr}`.
- Explosion de volumen de items si arrays son muy grandes.

## Decisiones abiertas

1. Nombre del campo de salida:
   - opcion A: reutilizar el mismo nombre de variable (`arr: element`) (recomendado, simple).
   - opcion B: usar un nombre fijo (`item` o `split_item`).
2. Default de `include_other_input_fields`:
   - recomendado `true` por UX segura.
3. Limite maximo de expansion por seguridad (futuro):
   - ej. `max_split_items` configurable global.

---

## 10) Resumen de implementacion futura

Archivos a crear/modificar:

- Nuevo backend: `app/nodes/split.py`
- Actualizar registro: `app/codegen/generator.py`
- Nuevo frontend: `frontend/src/nodes/SplitNode.jsx`
- Actualizar catalogo: `frontend/src/nodes/index.js`
- Documentacion: checklist/requirements tras implementar

Resultado esperado:

- El nodo `split` permite dividir arrays en items del flujo, con opcion de conservar contexto por item, alineado al comportamiento general del motor.
