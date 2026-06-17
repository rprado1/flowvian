# Plan de Implementacion - Nodo OpenAI Responses Create

## Estado

Documento de planificacion. **No contiene implementacion**.

## Objetivo

Agregar un nuevo nodo que permita invocar el endpoint de OpenAI Responses Create:

- Referencia: `POST /responses`
- Doc: `https://developers.openai.com/api/reference/resources/responses/methods/create`

Con parametros minimos requeridos por este alcance:

- `base_url`
- `api_key`
- `model`
- `message` (se mapeara a `input` del API)
- `instructions`
- `temperature`

## Alcance

Incluye:

- Nodo backend + frontend (canvas + formulario).
- Registro del nodo en `NODE_REGISTRY` y `NODE_META`.
- Generacion de codigo para ejecutar la llamada HTTP a Responses API.
- Validaciones minimas de configuracion.
- Soporte de templates `${VAR}` y secretos `#{SECRET}` en campos string.

No incluye (esta fase):

- Streaming de respuesta.
- Tool calling avanzado.
- Adjuntos multimedia.
- Manejo de conversaciones persistentes fuera del item actual.

## Diseno Funcional del Nodo

### Nombre y tipo

- Node type: `openai_responses`
- Label UI: `OpenAI Responses`

### Entradas / salidas

- Inputs: 1
- Outputs: 1

### Configuracion propuesta

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "#{OPENAI_API_KEY}",
  "model": "gpt-5-mini",
  "message": "[{\"role\":\"user\",\"content\":\"hello\"}]",
  "instructions": "You are a helpful assistant.",
  "temperature": 0.7,
  "include_other_input_fields": true,
  "output_var": "openai_response"
}
```

Notas:

- `message` se recibira en UI como texto (JSON) y se enviara como `input` al API.
- `message` debe permitir placeholders del flujo, incluyendo variables `${VAR_NAME}` y secretos `#{SECRET_NAME}`.
- `api_key` debe aceptar `#{SECRET_NAME}` para no exponer credenciales.
- `output_var` define donde se guarda la salida principal en `_out`.

## Mapeo al API OpenAI Responses

El request final se construye asi:

- URL: `{base_url}/responses`
- Headers:
  - `Authorization: Bearer <api_key>`
  - `Content-Type: application/json`
- Body JSON:
  - `model`
  - `input` (desde `message`)
  - `instructions`
  - `temperature`

## Cambios Backend

### 1) Nuevo nodo

Crear archivo:

- `app/nodes/openai_responses.py`

Responsabilidades:

- `validate()`:
  - `base_url`, `api_key`, `model`, `message` no vacios.
  - `temperature` numerica y en rango razonable (ej. 0 a 2).
  - `message` parseable a JSON valido para `input`.
- `to_code()`:
  - Resolver templates/secretos.
  - Construir request HTTP.
  - Manejar errores HTTP y de parseo.
  - Guardar respuesta estructurada en `output_var`.

### 2) Registro del nodo

Actualizar:

- `app/codegen/generator.py` (`NODE_REGISTRY`).

### 3) Salida estandar del nodo

Propuesta de salida en `_out[output_var]`:

- `ok` (bool)
- `status_code` (int|None)
- `response` (objeto JSON completo del endpoint)
- `text` (best-effort: texto sintetizado desde la respuesta)
- `error_message` (str|None)

## Cambios Frontend

### 1) Componente del nodo

Crear:

- `frontend/src/nodes/OpenaiResponsesNode.jsx`

Con:

- Card del nodo para canvas.
- `OpenaiResponsesPropsForm` con campos:
  - `base_url`
  - `api_key` (input password, no visible en claro)
  - `model`
  - `message` (textarea JSON)
  - `instructions` (textarea)
  - `temperature` (number)
  - `output_var`
  - `include_other_input_fields`

### 2) Registro en indice de nodos

Actualizar:

- `frontend/src/nodes/index.js`

Agregar:

- `nodeTypes.openai_responses`
- `NODE_META.openai_responses` con `defaultConfig` y `PropsForm`.

## Seguridad

- No loggear `api_key` ni headers de autorizacion.
- Permitir uso de `#{...}` en `api_key` para tomar secreto descifrado en runtime.
- Permitir en `message` tanto `${...}` como `#{...}` sin exponer secretos en logs.
- En UI, mostrar `api_key` enmascarada.

## Validaciones y Errores

- Si `message` no es JSON valido, error explicito de nodo.
- `message` debe resolver placeholders `${...}` y `#{...}` antes de enviar a OpenAI.
- Si `base_url` invalida, error claro.
- Si la API responde error, retornar detalle sanitizado en `error_message`.
- Si falta secreto referenciado, heredar error contextual existente (`Missing secret ... (node: ...)`).

## Plan por Fases

### Fase A - Backend base

1. Crear `OpenaiResponsesNode` con validacion y generacion de codigo.
2. Registrar nodo en `NODE_REGISTRY`.

### Fase B - Frontend

1. Crear `OpenaiResponsesNode.jsx` y su `PropsForm`.
2. Registrar nodo en `frontend/src/nodes/index.js`.

### Fase C - Integracion y pruebas

1. Probar guardado/carga de configuracion del nodo.
2. Probar llamada real a API con secreto en `api_key`.
3. Validar salida en rama terminal y manejo de errores.

## Criterios de Aceptacion

1. Existe nodo `openai_responses` disponible en el editor.
2. El nodo permite configurar `base_url`, `api_key`, `model`, `message`, `instructions`, `temperature`.
3. `message` se envia como `input` al endpoint `/responses`.
4. `message` soporta `${VAR}` y `#{SECRET}` para usar variables y secretos del flujo.
5. No se expone `api_key` en UI/logs.
6. La salida del nodo queda disponible para nodos siguientes en `output_var`.

## Riesgos y Mitigaciones

- Riesgo: formato variable de respuesta entre modelos.
  - Mitigacion: guardar respuesta completa + extraer `text` con best-effort.
- Riesgo: errores por JSON invalido en `message`.
  - Mitigacion: validacion en frontend y backend.
- Riesgo: credenciales mal configuradas.
  - Mitigacion: mensajes claros y soporte de secretos `#{...}`.
