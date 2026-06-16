# Plan de Implementacion - `W_METADATA_1` (clave maestra) + tipo `secret` en Set Variables

## Estado

Documento de planificacion. **No contiene implementacion**.

## Cambio de Enfoque (decision)

Se reemplaza el diseno anterior basado en base de datos SQLite de secretos.

Nueva estrategia:

- `W_METADATA_1` contiene **solo la clave maestra** para descifrar.
- `W_METADATA_1` **no** es JSON ni metadata serializada.
- Por el momento **no se usa SQLite** para secretos.
- Se agrega un nuevo tipo de variable `secret` en el nodo **Set Variables**.
- Los valores `secret` se guardan de forma dinamica en la configuracion del nodo, pero **cifrados** al persistir el workflow.
- En UI, los valores `secret` nunca se muestran en claro (siempre `********`).
- En runtime, las referencias `#{SECRET_NAME}` deben resolverse con descifrado previo.

## Objetivo

Implementar gestion de secretos sin DB, soportando:

- Declaracion de variables de tipo `secret` en Set Variables.
- Enmascaramiento total de secretos en portal.
- Resolucion segura de placeholders `#{SECRET_NAME}` durante ejecucion.
- Compatibilidad con placeholders normales `${VAR_NAME}` sin romper comportamiento actual.

## Alcance

Incluye:

- Lectura de `W_METADATA_1` como clave maestra en backend/runtime.
- Logica de descifrado usando `W_METADATA_1`.
- Nuevo tipo `secret` en backend y frontend del nodo Set Variables.
- Cifrado automatico de valores `secret` al guardar nodo/workflow.
- Enmascaramiento en UI y en respuestas API para campos sensibles.
- Soporte explicito de placeholder de secreto `#{...}`.

No incluye:

- Persistencia de secretos en SQLite.
- Pantalla CRUD dedicada de secretos.
- Integracion con KMS externo en esta fase.

## Suposicion Operativa de `W_METADATA_1`

`W_METADATA_1` contiene exclusivamente la **clave maestra** de descifrado.

Notas:

- El valor de `W_METADATA_1` no debe imprimirse en logs.
- Debe validarse presencia y formato minimo de clave (longitud/base64 segun algoritmo elegido).

## Reglas Funcionales

### 1) Tipo `secret` en Set Variables

- El selector de tipo del nodo Set Variables agrega opcion `secret`.
- Si una variable es `secret`:
  - En UI se visualiza ofuscada (`********`).
  - No se devuelve plaintext en API de lectura del workflow.
  - Se mantiene la clave/nombre para poder referenciarla.

### 2) Placeholders soportados

- `${VAR_NAME}`: comportamiento actual para variables normales.
- `#{SECRET_NAME}`: nuevo comportamiento:
  1. Detectar patron.
  2. Obtener el `ciphertext` del secreto desde la configuracion persistida del nodo Set Variables.
  3. Descifrar usando clave maestra de `W_METADATA_1`.
  4. Reemplazar placeholder por plaintext solo en memoria durante ejecucion.

### 3) Regla de no exposicion

- Nunca mostrar valores de secretos en pantalla.
- Nunca persistir secretos descifrados en BD de workflows.
- Nunca incluir secretos en logs de ejecucion, errores o previews.

## Diseno Tecnico Propuesto

### 1) Resolver de metadata y secretos

Crear modulo dedicado, por ejemplo `app/security/metadata_secrets.py`, con funciones:

- `load_master_key_from_env() -> str`
- `encrypt_secret_value(plaintext: str, master_key: str) -> str`
- `decrypt_secret_value(ciphertext: str, master_key: str) -> str`
- `resolve_secret_placeholders(text: str, available_secrets: dict, master_key: str) -> str`

Consideraciones:

- Cache en memoria por ejecucion para no descifrar repetidamente el mismo secreto.
- Errores claros cuando falte secreto en el flujo o la clave maestra sea invalida.

### 2) Integracion con motor de templates

Actualmente existe resolucion de `${...}` para variables del flujo. Debe extenderse para orden de resolucion:

1. Resolver `#{...}` (secretos, con descifrado).
2. Resolver `${...}` (variables de item/contexto).

Razon: evitar colisiones y asegurar separacion semantica entre variable comun y secreto.

### 3) Nodo Set Variables (backend)

Cambios esperados:

- Aceptar `type = secret` en validaciones.
- Mantener compatibilidad con tipos actuales (`string`, `number`, `boolean`, etc.).
- Impedir serializar/retornar en claro el valor de variables `secret` en endpoints de lectura.

### 4) Nodo Set Variables (frontend)

Cambios esperados en PropsForm:

- Nuevo tipo en selector: `Secret`.
- Input de valor tipo password para `secret`.
- Mostrar siempre mascara (`********`) al volver a abrir configuracion.
- Opcion de reemplazo de valor sin necesidad de revelar el actual.

### 5) Persistencia del workflow

Como por el momento no se usara SQLite para secretos, se define:

- Al guardar el nodo Set Variables, si `type=secret`, el `value` se cifra antes de persistir.
- En la persistencia del workflow se guarda el `ciphertext` (no plaintext).
- En lecturas para UI/API se devuelve valor enmascarado (`********`) para entries `secret`.

Decision recomendada: cifrado en persistencia del nodo + descifrado solo en runtime.

## Flujo de Ejecucion Esperado

1. Runtime carga y valida `W_METADATA_1` como clave maestra.
2. Workflow ejecuta nodos.
3. El motor construye un mapa de secretos disponibles desde nodos Set Variables (tipo `secret`) usando sus valores cifrados.
4. Cuando un campo contiene `#{SECRET_NAME}`:
   - se obtiene el `ciphertext` del mapa de secretos del flujo,
   - se descifra secreto en memoria,
   - se reemplaza en el texto final,
   - se continua ejecucion sin loggear valor.
5. `${VAR_NAME}` continua resolviendo desde contexto normal del flujo.

## Plan de Ejecucion por Fases

### Fase A - Contrato y parser

1. Definir contrato final de `W_METADATA_1` como clave maestra (no JSON).
2. Implementar loader/validator de clave desde env.
3. Implementar encrypter/decrypter base y manejo de errores.

### Fase B - Motor de placeholders

1. Extender resolucion para `#{...}`.
2. Integrar orden de resolucion `#{...}` luego `${...}`.
3. Agregar pruebas smoke de reemplazo mixto.

### Fase C - Set Variables

1. Backend: aceptar `type=secret`, cifrar al guardar y sanitizar respuestas.
2. Frontend: agregar tipo `Secret` y mascara constante.
3. Soportar reemplazo de valor secreto sin visualizacion del actual.

### Fase D - Seguridad y validacion

1. Revisar logs para evitar fugas de secretos.
2. Verificar que valores `secret` quedan cifrados en la persistencia del workflow.
3. Validar ejecucion end-to-end en VPS con `W_METADATA_1`.

## Criterios de Aceptacion (actualizados)

1. El sistema **no usa base de datos de secretos** independiente.
2. Existe tipo `secret` en Set Variables.
3. Al guardar nodo/workflow, los valores `secret` se almacenan cifrados.
4. Los secretos no se muestran en texto plano en el portal (`********`).
5. El formato `#{SECRET_NAME}` se detecta y resuelve con descifrado desde `W_METADATA_1`.
6. El formato `${VAR_NAME}` sigue funcionando como hasta ahora.
7. No se exponen secretos en logs, respuestas API ni vistas de ejecucion.

## Riesgos y Mitigaciones

- Riesgo: `W_METADATA_1` ausente o con formato invalido de clave.
  - Mitigacion: validacion temprana + error claro de configuracion.
- Riesgo: fuga por logs/debug.
  - Mitigacion: sanitizacion centralizada y pruebas de no-regresion.
- Riesgo: confundir `${...}` con `#{...}` en UX.
  - Mitigacion: ayuda contextual en UI y validaciones de formato.

## Definiciones Pendientes antes de implementar

- Formato exacto de la clave en `W_METADATA_1` (raw/base64, longitud, encoding).
- Algoritmo de cifrado/descifrado estandar del proyecto.
- Regla de resolucion cuando existan multiples nodos con el mismo `SECRET_NAME`.
- Politica cuando falta un secreto referenciado (fallar nodo vs valor vacio).
- Longitud maxima permitida para nombres de secretos.

## Entregables

- Ajustes de backend (metadata loader, decrypter, resolver `#{...}`).
- Ajustes frontend y backend del nodo Set Variables (`type=secret`).
- Documentacion de configuracion de `W_METADATA_1` y ejemplos.
- Evidencia de pruebas smoke y validaciones de seguridad.
