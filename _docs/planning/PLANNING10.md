# PLANNING10 — Corregir salida del EXE con Scheduler

## Objetivo

Corregir dos problemas en el script generado para EXE cuando existe nodo `scheduler`:

1. La salida impresa por iteracion no respeta el formato por ramas (`final_output`), imprime `_items` plano.
2. Los resultados se van acumulando entre iteraciones (cada 5s, etc.) en lugar de reiniciarse por ejecucion.

---

## Diagnostico (causa raiz)

### Problema A — Salida no es por ramas en EXE

En `app/codegen/generator.py`, dentro de `generate_script()` (caso scheduler), despues de cerrar el loop se emite:

```python
print(json.dumps(_items, default=str))
```

Esto ignora `_final_output` y por eso el EXE no muestra `{"mode":"by_terminal_branch", ...}` por iteracion.

### Problema B — Acumulacion entre iteraciones

En el script EXE, `_items` se inicializa una sola vez fuera del `while True`.

Luego `_emit_waves()` toma `_items` como seed (`_items_seed = list(_items)`), por lo que la siguiente vuelta del scheduler reutiliza la salida anterior como entrada base, concatenando resultados de ejecuciones previas.

---

## Semantica esperada

Cada tick del scheduler debe comportarse como una ejecucion nueva:

- nuevo `executionId`,
- nuevo `executionDate`,
- seed inicial limpio `[workflowId, executionId, executionDate]`,
- salida por tick en formato `final_output` por ramas terminales,
- sin arrastre de datos de ticks anteriores.

---

## Plan de cambios

### 1) `app/codegen/generator.py` — reinicio por iteracion en scheduler

En `generate_script()` (ramo `if scheduler_wave_idx is not None`):

- Antes de ejecutar waves dentro de `while True`, re-inicializar por iteracion:
  - `EXECUTION_ID = str(uuid.uuid4())`
  - `_items = [{"workflowId": WORKFLOW_ID, "executionId": EXECUTION_ID, "executionDate": datetime.now(timezone.utc).isoformat()}]`
  - `_final_output = {}` (limpiar salida previa)

**Importante:** esta reinicializacion debe quedar indentada dentro del `while True` (nivel loop body).

### 2) `app/codegen/generator.py` — salida por iteracion

En el mismo ramo scheduler, cambiar el print al final de cada tick:

- de `print(json.dumps(_items, default=str))`
- a `print(json.dumps(_final_output, default=str))`

Asi la salida del EXE queda alineada con el portal/run API.

### 3) `app/codegen/generator.py` — consistencia del estado global

Confirmar que `WORKFLOW_MAIN_START` declare `global _items, _final_output` (ya esta).

Verificar que `_emit_waves()` siga construyendo por tick:

- `_terminal_branches`
- `_final_output = {'mode': 'by_terminal_branch', ...}`

sin depender de estado previo.

### 4) No tocar contrato de API run

`generate_run_script()` ya devuelve `final_output` por ejecucion unica y no sufre acumulacion por scheduler (usa `range(1)`).

No se requieren cambios funcionales en `app/api/builder.py` para este bug.

---

## Verificacion

### A. Smoke backend

```bash
python -c "from app.main import app; print('OK')"
```

### B. Preview de script con scheduler

1. Generar preview de workflow con scheduler.
2. Confirmar en el codigo generado que dentro del `while True`:
   - se re-crea `EXECUTION_ID`,
   - se re-crea `_items` seed,
   - se limpia `_final_output`,
   - el `print` usa `_final_output`.

### C. Ejecucion manual del `.py` generado (sin PyInstaller)

1. Ejecutar script 2-3 ciclos.
2. Confirmar que cada linea impresa tiene `mode: by_terminal_branch`.
3. Confirmar que `executionId` cambia en cada ciclo.
4. Confirmar que no crece la cantidad de items por arrastre de ciclos previos.

### D. EXE

1. Build del workflow.
2. Ejecutar EXE por varios ciclos.
3. Confirmar mismo comportamiento que en C.

---

## Criterio de aceptacion

- El EXE con scheduler imprime salida por tick en formato `final_output` por ramas.
- No existe acumulacion de resultados entre ticks consecutivos.
- Cada tick tiene `executionId` nuevo y seed limpio.
- El comportamiento del portal (`/run`) y del EXE queda alineado semanticamente.
