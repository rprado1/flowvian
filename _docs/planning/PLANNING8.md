# Plan de Implementacion - Salida minima en consola para Scheduler (EXE)

## Estado

Documento de planificacion. **No contiene implementacion**.

## Objetivo

Cuando el workflow tenga como nodo inicial un `scheduler` y se ejecute como archivo ejecutable, la consola debe mostrar solo:

- `Nombre del workflow`
- `Aplicacion iniciada`

No deben mostrarse logs ni salidas de debug en consola durante la ejecucion normal.
Los errores deben seguir registrandose en archivo `*_errors.log` como hoy.

## Alcance

Incluye:

- Ajuste del codigo generado para workflows con scheduler en modo script/exe.
- Banner de inicio controlado en consola para scheduler.
- Silenciar salida de runtime (prints de output por iteracion y logs en consola).
- Mantener registro de errores en archivo de log.

No incluye (esta fase):

- Cambios de comportamiento para workflows con trigger `webhook`.
- Cambios de UX del editor.
- Nuevo sistema de niveles de log configurable por UI.

## Regla Funcional Principal

### 1) Scheduler en ejecutable

Si el flujo inicia con `scheduler`:

- Al arrancar el proceso se imprime una sola vez:
  - `<Nombre del workflow>`
  - `Aplicacion iniciada`
- No se imprime en consola el `json.dumps(_final_output)` en cada ciclo.
- No se imprimen trazas informativas de runtime.

### 2) Manejo de errores

- Ante excepcion no controlada, el detalle tecnico sigue yendo a `*_errors.log`.
- En consola no se agregan mensajes de ruido; se mantiene salida minima definida.
- Se conserva `stderr` para fallos fatales solo si ya existe contrato externo que lo requiera.

## Analisis Tecnico (estado actual)

Archivo clave:

- `app/codegen/generator.py`

Puntos relevantes del generador:

1. `SCRIPT_HEADER` configura logging a archivo (`filename=_log_path`, `level=ERROR`).
2. En `generate_script()`, rama con scheduler agrega dentro del loop:
   - `print(json.dumps(_final_output, default=str))`
3. Ese `print` produce salida continua en consola y hoy se percibe como logs.

## Diseno Propuesto

### 1) Banner de arranque para scheduler

Agregar emision explicita de mensaje de arranque una sola vez en la rama scheduler de `generate_script()`:

- `print(WORKFLOW_NAME)`
- `print("Aplicacion iniciada")`

Ubicacion sugerida:

- Dentro de `_run()`, antes de entrar al `while True` del scheduler o justo despues de construir el loop, garantizando ejecucion unica por proceso.

### 2) Eliminar salida por iteracion

Retirar en rama scheduler la linea:

- `print(json.dumps(_final_output, default=str))`

Resultado esperado:

- Cada tick sigue ejecutando nodos, pero sin salida de consola.

### 3) Mantener errores en archivo

No modificar bloque de error actual en `WORKFLOW_MAIN_END` que hace:

- `_logger.error("Unhandled exception..."...)`

Esto preserva el log de errores en archivo junto al ejecutable.

### 4) Compatibilidad con otros triggers

No tocar comportamiento actual de:

- rama no-scheduler (run unico).
- rama webhook.

## Criterios de Aceptacion

1. Workflow con nodo inicial `scheduler` en EXE muestra solo dos lineas al iniciar:
   - nombre del workflow,
   - `Aplicacion iniciada`.
2. Durante la ejecucion periodica no aparecen nuevas lineas en consola.
3. Si ocurre error, se registra en `*_errors.log`.
4. Workflows sin scheduler no cambian su comportamiento actual salvo que se acuerde explicitamente.
5. Webhook mantiene su salida actual.

## Riesgos y Mitigaciones

- Riesgo: algun proceso externo depende del `print` JSON por tick.
  - Mitigacion: limitar cambio solo a rama scheduler y documentarlo.
- Riesgo: perdida de visibilidad operativa en consola.
  - Mitigacion: mantener archivo de errores y opcion futura de modo verbose por env var.
- Riesgo: confusion entre build script y run script instrumentado.
  - Mitigacion: aplicar cambio solo en `generate_script()` (script final para EXE), no en `generate_run_script()`.

## Plan por Fases

### Fase A - Ajuste en generador

1. Identificar bloque scheduler en `generate_script()`.
2. Insertar banner de inicio de dos lineas.
3. Quitar `print(json.dumps(_final_output, default=str))` del loop scheduler.

### Fase B - Verificacion rapida

1. `python -m py_compile app/codegen/generator.py`
2. Generar script de un workflow con scheduler y revisar salida esperada.
3. Simular error y confirmar escritura en `*_errors.log`.

### Fase C - Documentacion

1. Registrar cambio de comportamiento en `README.md` o nota tecnica si aplica.
2. Aclarar que la consola del EXE scheduler es de salida minima.

## Archivos Objetivo

- `app/codegen/generator.py`
- `README.md` (opcional, si se decide documentar comportamiento)
