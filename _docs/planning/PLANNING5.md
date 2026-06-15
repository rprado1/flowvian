# PLANNING1 — Nodo Stop and Error (detiene solo la ejecución actual)

## 1) Objetivo

Diseñar el nodo `stop_and_error` para finalizar solamente la iteración o ejecución actual del flujo con un mensaje personalizado, sin detener el proceso global del motor.

El nodo debe:

- Marcar la ejecución actual como finalizada con error de negocio.
- Permitir placeholders `${VARIABLE}` en el mensaje.
- Evitar propagación de cancelación global.
- Permitir que otras iteraciones/lotes continúen normalmente.

En esta fase se documenta la propuesta técnica. No se implementa código todavía.

---

## 2) Alcance funcional

### Incluido

- Nodo nuevo `stop_and_error`.
- Input único.
- Campo `message` obligatorio.
- Interpolación `${VAR}` con el item actual.
- Finalización controlada del contexto actual (iteración/lote actual según punto de ejecución).
- Registro explícito del estado finalizado por stop.

### No incluido (por ahora)

- Retries automáticos.
- Continue-on-error configurable por nodo.
- Catálogo de códigos de error tipados (se puede extender luego).

---

## 3) Semántica correcta de ejecución

## Regla principal

`stop_and_error` no debe lanzar una excepción fatal que llegue al nivel top-level del script.

En su lugar debe usar una señal controlada y local para detener únicamente el contexto activo.

## Comportamiento esperado

- Se detiene la ejecución actual (la que está procesando ese nodo).
- No se detiene el worker/proceso.
- No se cancela el workflow global en curso.
- No se cancelan otras ramas independientes ya en ejecución.
- No se afectan otros items pendientes fuera del contexto actual.

---

## 4) Diseño técnico propuesto (backend)

## 4.1 Señal local de stop (sin cancelación global)

Agregar en el script generado una excepción interna controlada, por ejemplo:

- `_StopIterationExecution(Exception)`

Con payload:

- `message`
- `node_id`
- `node_type`
- `item_snapshot` (opcional para traza)

Esta excepción:

- Se usa solo para cortar el contexto de ejecución actual.
- Se captura en límites internos de ejecución (wave/branch/run loop), nunca dejando que llegue al manejador fatal global.

## 4.2 Nodo `stop_and_error`

Nuevo archivo `app/nodes/stop_and_error.py`:

- `NODE_TYPE = "stop_and_error"`
- `validate()`:
  - `message` requerido, no vacío.
- `to_code()`:
  - Resolver mensaje con `_resolve_template(message, _item)`.
  - Disparar señal local: `raise _StopIterationExecution(...)`.

Importante: no usar `ValueError`/`Exception` genérica para este caso.

## 4.3 Manejo en generador

Actualizar `app/codegen/generator.py` para:

1. Definir la clase `_StopIterationExecution` en `SCRIPT_HEADER` y `RUN_SCRIPT_HEADER`.
2. Capturar esa excepción en puntos de orquestación:
   - ejecución inline de nodo,
   - funciones de rama en waves paralelas,
   - consolidación de resultados por wave,
   - lazo de ejecución bajo scheduler.
3. Traducir la captura a estado de ejecución local finalizada, por ejemplo:
   - `_final_output['status'] = 'stopped_current_execution'`
   - `_final_output['stop_reason'] = <mensaje>`
   - `_final_output['stop_node'] = {...}`
4. Continuar con siguientes iteraciones del scheduler o siguientes ejecuciones del motor, sin terminar el proceso.

## 4.4 Propagación controlada en concurrencia

En waves paralelas:

- Si una rama dispara `_StopIterationExecution`, se marca esa rama como `stopped`.
- No usar cancelación global de `_futs` ni `shutdown(cancel_futures=True)`.
- Esperar finalización natural de otras ramas ya enviadas.
- Consolidar salida de la ejecución actual como detenida y cerrar esa ejecución.

Esto evita abortar trabajo concurrente no relacionado.

---

## 5) Cambios requeridos en frontend

## 5.1 Nuevo nodo React

Crear `frontend/src/nodes/StopAndErrorNode.jsx`:

- `inputs: 1`
- `outputs: 0` (semántica terminal para esa ejecución)
- icono sugerido `⛔`
- texto corto: `Stop current execution`

## 5.2 Props form

- Campo `message` (textarea)
- Hint: `You can use ${VARIABLE}`
- Validación visual si está vacío

## 5.3 Registro

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.stop_and_error`
- `NODE_META.stop_and_error` con default:

```json
{ "message": "Execution stopped by business rule" }
```

---

## 6) Modelo de datos del nodo

```json
{
  "message": "Customer ${customer_id} is not eligible"
}
```

Reglas:

- `message` string obligatorio.
- Placeholder faltante produce mensaje controlado de stop para esa ejecución actual.

---

## 7) Trazas, estado y observabilidad

## Run instrumentado

Registrar evento de nodo con estado específico:

- `status: 'stopped_current_execution'`
- `error` o `stop_reason` con mensaje final
- `items_in` del nodo

## Output final sugerido

Para la ejecución detenida:

```json
{
  "status": "stopped_current_execution",
  "stop_reason": "...",
  "stop_node": { "id": "...", "type": "stop_and_error" }
}
```

Sin terminar el proceso global.

---

## 8) Puntos a corregir para evitar finalización global

La lógica actual debe revisarse donde se hace `raise` genérico y se re-propaga hasta top-level:

1. Bloques `try/except` por nodo que hacen `raise` directo.
2. Recolección de `future.result()` en waves paralelas que re-lanza excepción fatal.
3. Handler principal `if __name__ == '__main__'` que sale con `sys.exit(1)` ante cualquier excepción.

Corrección propuesta:

- Distinguir `_StopIterationExecution` de errores fatales reales.
- Solo errores fatales reales deben llegar al manejador top-level.
- `_StopIterationExecution` debe convertirse en estado de ejecución finalizada local.

---

## 9) Casos de prueba sugeridos

## Funcionales

1. Flujo sin scheduler: `... -> stop_and_error -> ...`
   - Se finaliza solo esa ejecución actual, proceso sigue vivo.
2. Flujo con scheduler:
   - Una iteración dispara stop; la siguiente iteración se ejecuta normalmente.
3. Lote de múltiples items:
   - El stop afecta solo el contexto actual definido (según diseño), no colapsa todo el motor.

## Concurrencia

4. Wave con 2 ramas, una con stop y otra normal:
   - Rama normal completa.
   - No hay cancelación global de futures.
   - Se registra estado final local correcto.

## Errores

5. Excepción real de otro nodo (no stop):
   - Sí se trata como error fatal de ejecución (comportamiento actual para errores no controlados).

---

## 10) Riesgos y decisiones abiertas

## Riesgos

- Definir con precisión "ejecución actual" cuando hay paralelismo y múltiples items.
- Evitar mezclar stop de negocio con errores técnicos reales.

## Decisiones abiertas

1. En ejecución item-by-item, ¿stop corta solo el item actual o la corrida completa del lote actual?
2. ¿Se requiere código de error (`stop_code`) además de mensaje?
3. ¿Debe existir un nodo aparte `stop_silent` más adelante?

---

## 11) Resumen de implementación futura

Cambios mínimos esperados:

- Backend:
  - `app/nodes/stop_and_error.py` (nuevo)
  - `app/codegen/generator.py` (registro + excepción controlada + captura local)
- Frontend:
  - `frontend/src/nodes/StopAndErrorNode.jsx` (nuevo)
  - `frontend/src/nodes/index.js` (registro + defaults)
- Comportamiento:
  - stop local por ejecución actual
  - sin detener proceso global ni iteraciones futuras

Este enfoque cumple tu requisito: finalizar únicamente el contexto actual, mantener vivo el motor y permitir continuidad normal del resto de ejecuciones.
