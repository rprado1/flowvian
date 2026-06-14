# PLANNING — Nodo HTTP Request (GET/POST)

## 1) Objetivo

Diseñar un nuevo nodo `http_request` para consumir APIs REST dentro del workflow, con soporte inicial para:

- `GET`
- `POST`

El nodo debe permitir:

- URL configurable
- Headers personalizados
- Body raw JSON (solo para POST)
- Interpolación de variables del flujo con sintaxis `${NOMBRE_VARIABLE}` en URL, headers y body

En esta fase se documenta análisis y propuesta técnica. **No se implementa código aún**.

---

## 2) Alcance funcional

### Incluido

- Método: `GET` y `POST`
- URL string con placeholders
- Lista dinámica de headers (`key/value`)
- Body raw JSON para POST
- Timeout por nodo configurable
- Salida estandarizada para nodos posteriores

### No incluido (por ahora)

- PUT/PATCH/DELETE
- Form-data / multipart file upload
- Auth flows avanzados (OAuth handshake)
- Retries/backoff automáticos (se deja opcional para fase futura)

---

## 3) Diseño técnico propuesto

## Enfoque de implementación

- Backend Python: usar **stdlib** (`urllib.request`, `urllib.error`, `json`, `re`, `ipaddress`, `socket`), evitando dependencias nuevas.
- El nodo se ejecuta por item (como el resto): por cada `_item`, resuelve placeholders y realiza 1 request.
- Salida por item incluye metadatos HTTP y payload/errores.

## Comportamiento por método

- `GET`: usa URL + headers; ignora body.
- `POST`: usa URL + headers + body JSON resultante de interpolación y validación.

## Contrato de salida del nodo (propuesto)

Por cada `_item`, el nodo produce (nombres fijos):

- `http_status_code` (int | null)
- `http_response_headers` (dict)
- `http_response_body` (dict | list | str | null)
- `http_ok` (bool)
- `http_error_message` (str | null)

Opcional recomendado:

- `http_url_resolved` (str)
- `http_method` (str)

Compatibilidad con flujo actual:

- Mantener opción `include_other_input_fields` para mergear `_item` con `_out`.

---

## 4) Cambios requeridos en backend

## 4.1 Nuevo nodo

Crear `app/nodes/http_request.py` con clase `HttpRequestNode(BaseNode)`:

- `NODE_TYPE = "http_request"`
- `validate()`
  - método en `{GET, POST}`
  - URL no vacía y esquema `http|https`
  - timeout numérico en rango permitido
  - headers estructura válida (lista de pares o dict normalizado)
  - si método POST: `body_raw_json` obligatorio y JSON parseable (tras interpolación por item en runtime, ver estrategia)
- `to_code()`
  - genera bloque de request + manejo de excepciones
  - setea los campos de salida fijos

## 4.2 Registro

Actualizar `app/codegen/generator.py`:

- Importar `HttpRequestNode`
- Registrar en `NODE_REGISTRY`

## 4.3 Helpers recomendados en código generado

Agregar helpers reutilizables en header del script generado:

- `_resolve_template(text, item)` para `${VAR}`
- `_resolve_json_template(obj, item)` (resolución recursiva)
- `_validate_target_url(url)` (restricciones seguridad/SSRF)

Esto evita duplicar lógica en cada nodo y mantiene consistencia.

---

## 5) Cambios requeridos en frontend

## 5.1 Nuevo nodo React

Crear `frontend/src/nodes/HttpRequestNode.jsx` con:

- Componente canvas (icono sugerido `🌐`)
- Props form con campos:
  - `method` (select GET/POST)
  - `url`
  - `timeout_seconds`
  - headers dinámicos (`key/value`, add/remove)
  - `body_raw_json` (textarea; visible solo en POST)
  - `include_other_input_fields` (checkbox)

## 5.2 Registro del nodo

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.http_request`
- `NODE_META.http_request`
  - `inputs: 1`
  - `outputs: 1`
  - `defaultConfig` inicial
  - `PropsForm`

## 5.3 UX de validación

Validación inmediata en form (best effort):

- URL vacía
- JSON inválido en body (POST)
- headers con key vacía

Sin bloquear guardado agresivamente; backend sigue siendo fuente de verdad.

---

## 6) Modelo de datos del nodo

Config propuesta (`config` JSON):

```json
{
  "method": "GET",
  "url": "https://api.example.com/users/${USER_ID}",
  "headers": [
    {"key": "Authorization", "value": "Bearer ${TOKEN}"},
    {"key": "Content-Type", "value": "application/json"}
  ],
  "body_raw_json": "{\n  \"customerId\": \"${CUSTOMER_ID}\"\n}",
  "timeout_seconds": 30,
  "include_other_input_fields": true
}
```

Reglas:

- `body_raw_json` se ignora en GET.
- `timeout_seconds` default: `30`, rango sugerido: `1..120`.

---

## 7) Estrategia de interpolación de variables

Sintaxis soportada:

- `${NOMBRE_VARIABLE}`

Regex sugerido:

- `\$\{([A-Za-z_][A-Za-z0-9_]*)\}`

Resolución:

1. URL: reemplazo string directo.
2. Headers: reemplazo string directo en `value`.
3. Body JSON:
   - Parsear `body_raw_json` como objeto JSON *template*.
   - Recorrer recursivamente strings y aplicar reemplazo.
   - Si el string completo es exactamente `${VAR}`, preservar tipo original de `_item[VAR]` (number/bool/object/list/null).
   - Si `${VAR}` aparece embebido en texto, convertir valor a string.

Variables inexistentes (`${VARIABLE_INEXISTENTE}`):

- Propuesta: marcar request como error de nodo por item (sin lanzar excepción fatal global), seteando:
  - `http_ok = false`
  - `http_error_message = "Missing variable: VARIABLE_INEXISTENTE"`
  - `http_status_code = null`

---

## 8) Manejo de errores

## Política propuesta

El nodo no debe tumbar toda la ejecución por errores de red/HTTP/plantilla en un item. Debe producir salida de error por item y continuar con los demás items.

Mapeo sugerido:

- HTTP 4xx/5xx:
  - `http_ok = false`
  - `http_status_code = <code>`
  - `http_response_body` con payload de error si existe
  - `http_error_message = "HTTP <code>"`
- Timeout:
  - `http_ok = false`
  - `http_status_code = null`
  - `http_error_message = "Request timeout after Xs"`
- Error de red / DNS / conexión:
  - `http_ok = false`
  - `http_error_message` con mensaje normalizado
- JSON inválido en POST (tras interpolación):
  - `http_ok = false`
  - `http_error_message = "Invalid JSON body after interpolation"`

---

## 9) Consideraciones de seguridad

## SSRF / destino

- Permitir solo `http` y `https`.
- Bloquear hostnames/IP locales o privadas (loopback, link-local, RFC1918, multicast, unspecified).
- Resolver DNS y validar IP final antes de request.
- Revalidar tras redirecciones (si se permiten).

## Timeouts y límites

- Timeout por request con tope superior (p.ej. 120s).
- Limitar tamaño de body de request (p.ej. 1 MB).
- Limitar tamaño de response leído (p.ej. 2 MB) para evitar consumo excesivo.

## Headers sensibles

- Evitar logging completo de tokens (`Authorization`, `Cookie`).
- En trazas, opcional enmascarar valores sensibles.

## TLS

- Mantener verificación TLS por defecto (no permitir `verify=false` en esta fase).

---

## 10) Casos de prueba

## Funcionales

1. GET simple 200 con URL fija.
2. GET con `${USER_ID}` en URL.
3. GET con headers interpolados.
4. POST con `body_raw_json` válido e interpolación.
5. POST con body inválido -> error por item.

## Errores

6. Variable inexistente en URL/header/body.
7. Timeout forzado.
8. HTTP 400/401/403/404/500.
9. Host no resoluble / conexión rechazada.

## Seguridad

10. URL localhost (`http://127.0.0.1/...`) debe bloquearse.
11. URL privada (`http://10.x.x.x/...`) debe bloquearse.
12. Payload/response sobre límite debe fallar controladamente.

## Integración workflow

13. `Set Variables -> Http Request -> Merge` con múltiples items.
14. `include_other_input_fields=true` conserva contexto upstream.

---

## 11) Riesgos y preguntas abiertas

## Riesgos

- Complejidad de interpolación tipada en JSON.
- Falsos positivos/negativos en validación SSRF por DNS complejo.
- Cambios de contrato de salida si en el futuro se agregan retries o auth avanzada.

## Preguntas abiertas

1. ¿El comportamiento ante HTTP 4xx/5xx debe continuar flujo (propuesto) o fallar ejecución completa?
2. ¿Necesitamos opción configurable `fail_on_http_error`?
3. ¿Se deben permitir redirecciones? Si sí, ¿cuántas?
4. ¿Cuál será límite oficial de timeout por request (60, 120, 300)?
5. ¿Se necesita almacenar response body completo o truncado para payloads grandes?
6. ¿Se requiere mapear resultado a nombres configurables (prefijo/alias) además de campos fijos?

---

## Resumen de implementación futura

Cambios mínimos esperados cuando se ejecute esta planificación:

- Backend:
  - `app/nodes/http_request.py` (nuevo)
  - `app/codegen/generator.py` (registro)
  - helpers de interpolación y seguridad en script generado
- Frontend:
  - `frontend/src/nodes/HttpRequestNode.jsx` (nuevo)
  - `frontend/src/nodes/index.js` (registro)
  - validaciones básicas en formulario

Esta propuesta cumple el requerimiento solicitado y mantiene compatibilidad con el modelo actual de ejecución por items.
