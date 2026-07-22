# Plan: Mejorar columna `Time` en tabla de resultados (Inicio y Fin)

## Objetivo

Actualizar la tabla **Run Results** del frontend para que la columna `Time` muestre claramente dos valores por fila:

- **Inicio**
- **Fin**

en lugar de un unico timestamp.

## Contexto tecnico actual

- La tabla se renderiza en `frontend/src/components/RunPanel.jsx`.
- Hoy la columna `Time` usa `tr.ts` y muestra solo `toLocaleTimeString()`.
- El backend (trazas generadas en `app/codegen/generator.py`) actualmente registra `ts` por nodo, sin separar inicio y fin.

## Estrategia propuesta

### 1) Definir contrato de trazas para tiempo de inicio/fin

- Extender cada traza de nodo para incluir:
  - `start_ts` (epoch seconds)
  - `end_ts` (epoch seconds)
- Mantener `ts` temporalmente por compatibilidad durante la migracion.
- Criterio de consistencia:
  - `start_ts`: justo antes de ejecutar el nodo.
  - `end_ts`: inmediatamente al terminar (ok/error/stopped).

### 2) Actualizar generacion de trazas en backend

- En `app/codegen/generator.py`, en los bloques donde se construye `_trace.append(...)`:
  - Capturar `time.time()` en variable local al inicio de cada nodo (ej. `_node_start_ts`).
  - Reusar `time.time()` al finalizar (ej. `_node_end_ts`).
  - Agregar ambos campos al objeto de traza para los tres estados:
    - `ok`
    - `error`
    - `stopped_current_execution`
- Revisar ramas especiales (por ejemplo webhook) para mantener el mismo contrato de campos.

### 3) Actualizar UI de la columna `Time`

- En `frontend/src/components/RunPanel.jsx`:
  - Cambiar encabezado de columna de `Time` a `Inicio / Fin` (o mantener `Time` con contenido doble, segun estilo actual del equipo).
  - Renderizar en dos lineas:
    - `Inicio: HH:mm:ss`
    - `Fin: HH:mm:ss`
  - Implementar helper para formatear timestamps de forma segura.
- Compatibilidad:
  - Si faltan `start_ts` o `end_ts`, usar fallback con `tr.ts` o `—` para evitar romper runs antiguos.

### 4) Ajuste visual y legibilidad

- Verificar ancho de columna para evitar cortes innecesarios en mobile.
- Mantener clases existentes (`text-xs`, `text-muted-foreground`) y estructura de tabla sin cambios disruptivos.

### 5) Validacion

#### Validacion funcional

- Ejecutar un workflow simple y confirmar por cada fila:
  - `Inicio` visible.
  - `Fin` visible.
  - Orden temporal correcto (`Fin >= Inicio`).
- Probar casos de estado:
  - `ok`
  - `error`
  - `stopped_current_execution`

#### Validacion tecnica minima

- Frontend lint:
  - `cd frontend && npm run lint -- src/components/RunPanel.jsx`
- Smoke backend:
  - `python -c "from app.main import app; print('OK')"`

## Riesgos y mitigaciones

- **Riesgo:** traces antiguas sin nuevos campos.
  - **Mitigacion:** fallback en frontend (`start_ts/end_ts -> ts -> —`).
- **Riesgo:** inconsistencias en rutas de generacion de trace (normal vs webhook).
  - **Mitigacion:** checklist de puntos `_trace.append(...)` y verificacion manual en ambos flujos.

## Entregables

- Cambios en contrato de trace y generacion en `app/codegen/generator.py`.
- Cambios de render de columna `Time` en `frontend/src/components/RunPanel.jsx`.
- Verificacion funcional con ejecucion real de workflow.

## Criterios de aceptacion

- La columna de tiempo muestra **Inicio** y **Fin** por nodo en la tabla de resultados.
- No se rompe la visualizacion de ejecuciones anteriores o incompletas.
- El frontend compila/linta sin errores en el archivo modificado.
