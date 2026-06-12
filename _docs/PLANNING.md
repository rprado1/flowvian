# PLANNING — Requerimiento #16: Botón Run + Tabla de Resultados

## Objetivo

Agregar un botón **▶ Run** en el portal que ejecute el workflow y muestre en un panel inferior una tabla con los datos de entrada/salida de cada nodo ejecutado.

## Arquitectura

```
[Frontend]                     [Backend]
    │                              │
    ├─ POST /run ────────────────► │
    │                              ├─ generate_run_script() → script instrumentado
    │                              ├─ subprocess.run(script) → trace.jsonl
    │                              ├─ leer trace.jsonl
    │◄─ { traces: [...] } ────────┤
    │                              │
    ├─ renderRunResults(traces)    │
    └─ Tabla: nodo | tipo | estado | entrada | salida
```

## Cambios necesarios

### 1. Backend: `app/codegen/generator.py`
- Nueva función `generate_run_script()` que envuelve cada nodo con captura de `locals()` antes/después
- El script instrumentado escribe un archivo JSONL con las trazas de ejecución
- Ejecuta solo una iteración del loop (si hay Scheduler, solo 1 iteración)
- Timeout de 30s para la ejecución
- Importa `json`, `sys` y escribe trazas a un archivo temporal

### 2. Backend: `app/api/builder.py`
- Nuevo endpoint `POST /api/workflows/{id}/run`
- Genera script instrumentado → lo guarda en `output/{id}/run_script.py`
- Ejecuta con `subprocess.run()` → captura salida
- Lee archivo de trazas JSONL → devuelve array de trazas

### 3. Frontend: `app/static/index.html`
- Botón `▶ Run` en la topbar
- Panel inferior `#run-panel` con tabla de resultados (inicialmente oculto)

### 4. Frontend: `app/static/js/app.js`
- `runWorkflow()` → llama al endpoint, muestra spinner, renderiza resultados
- `renderRunResults(traces)` → pinta tabla con entrada/salida por nodo

### 5. Frontend: `app/static/css/style.css`
- Estilos para `#run-panel` y tabla de resultados
