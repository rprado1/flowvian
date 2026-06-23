# Plan de Implementacion - Variables Globales en `set_variables` con selector `Local/Global`

## Estado

Documento de planificacion. **No contiene implementacion**.

## Objetivo

Actualizar el nodo `set_variables` para que cada variable pueda definir su alcance (`scope`) con un nuevo selector **encima** del selector de modo de valor (`Literal`, `Template`, `Path`):

- `Local` (por defecto)
- `Global`

Cuando una variable se marque como `Global`, podra reutilizarse en cualquier nodo mediante el template `@{VAR}`.

## Alcance

Incluye:

- Frontend: nuevo selector `Local/Global` por variable en `SetVariablesPropsForm`, ubicado encima del selector de modo de valor.
- Backend `set_variables`: aceptar y validar `scope` por variable.
- Runtime/codegen: soporte de placeholders globales `@{VAR}` en resolucion de templates.
- Inicializacion del store global por ejecucion (sin persistencia entre runs).

No incluye (esta fase):

- Persistencia de variables globales en base de datos separada del grafo.
- Fallback automatico entre `${VAR}` y `@{VAR}`.

## Reglas Funcionales

### 1) Estructura por variable

Cada item de `config.variables` tendra (ademas de lo actual) un campo `scope`:

```json
{
  "key": "API_BASE",
  "scope": "global",
  "value_mode": "literal",
  "type": "string",
  "value": "https://api.example.com"
}
```

Valores permitidos:

- `scope`: `local` | `global`
- `value_mode`: `literal` | `template` | `path`

Default de compatibilidad:

- Si `scope` no existe en configuraciones antiguas, se asume `local`.

### 2) Semantica de alcance

- `local`: comportamiento actual (se escribe en `_out` para el item).
- `global`: mantiene escritura en `_out` y ademas guarda el valor en un store global de ejecucion.

### 3) Placeholder global

Se agrega soporte para:

- `@{VAR_NAME}`: lee desde store global.

Compatibilidad:

- `${VAR}` mantiene lectura desde `_item`.
- `#{SECRET}` mantiene lectura desde `_secret_store`.

## Diseno Frontend

Archivo principal:

- `frontend/src/nodes/SetVariablesNode.jsx`

Cambios:

1. Agregar un nuevo `<select>` para `scope` por variable.
2. Ubicar el selector de `scope` **encima** del selector actual `Literal/Template/Path`.
3. Valor por defecto al crear variable nueva:
   - `scope: 'local'`
4. Mantener selector actual de `value_mode` sin cambiar sus opciones.
5. Ajustar texto de ayuda para explicar `@{VAR}` cuando `scope` sea `global`.

## Diseno Backend (`set_variables`)

Archivo:

- `app/nodes/set_variables.py`

Cambios:

1. Normalizar `scope` (`local` por defecto).
2. Validar que `scope` sea `local` o `global`.
3. En `to_code()`:
   - resolver valor segun `value_mode` y `type` como hoy,
   - guardar siempre en `_out[_sv_key]`,
   - si `scope == 'global'`, guardar tambien en `_global_store[_sv_key]`.

## Diseno Runtime / Codegen

Archivo:

- `app/codegen/generator.py`

Cambios:

1. Agregar regex global:
   - `_GLOBAL_VAR_RE = re.compile(r"@\\{([A-Za-z_][A-Za-z0-9_]*)\\}")`
2. Agregar store de ejecucion:
   - `_global_store = {}`
3. Agregar helper:
   - `_resolve_global_placeholders(_text)` para reemplazar `@{...}`.
4. Integrar resolucion global en `_resolve_template()` y `_resolve_json_template()`.
5. Reiniciar `_global_store` al iniciar ejecucion normal y por request en webhook.

## Orden de Resolucion de Placeholders

Orden recomendado en templates de texto:

1. `#{SECRET}`
2. `@{GLOBAL}`
3. `${ITEM}`

## Criterios de Aceptacion

1. En `set_variables`, cada variable muestra selector `Local/Global` encima del selector de `Literal/Template/Path`.
2. Las variables nuevas inician con `Local` por defecto.
3. Si una variable se marca `Global`, puede usarse en cualquier nodo con `@{VAR}`.
4. Si una variable global referenciada no existe, se devuelve error claro.
5. Workflows existentes siguen funcionando (sin `scope` explicito => `local`).
6. En webhook, las globales se limpian por request.

## Riesgos y Mitigaciones

- Riesgo: colision de nombres globales en ramas paralelas.
  - Mitigacion: documentar comportamiento de ultima escritura y recomendar nombres unicos.
- Riesgo: confusion de sintaxis entre `${VAR}` y `@{VAR}`.
  - Mitigacion: textos de ayuda en UI y ejemplos en README.

## Plan por Fases

### Fase A - Runtime

1. Implementar `_GLOBAL_VAR_RE`, `_global_store`, y resolucion `@{...}`.
2. Reiniciar store global en todos los entrypoints de ejecucion.

### Fase B - Nodo backend

1. Agregar normalizacion/validacion de `scope` en `set_variables`.
2. Escribir en `_global_store` cuando `scope == 'global'`.

### Fase C - Frontend

1. Agregar selector `Local/Global` encima del selector de modo.
2. Definir default `local` al crear variables.
3. Ajustar ayudas visuales.

### Fase D - Verificacion

1. `python -c "from app.main import app; print('OK')"`
2. `python -m py_compile app/main.py app/codegen/generator.py app/nodes/set_variables.py`
3. `cd frontend && npm run lint -- src/nodes/SetVariablesNode.jsx`

## Archivos Objetivo

- `frontend/src/nodes/SetVariablesNode.jsx`
- `app/nodes/set_variables.py`
- `app/codegen/generator.py`
- `README.md` (seccion de placeholders, si aplica)
