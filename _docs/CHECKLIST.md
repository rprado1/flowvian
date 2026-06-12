# CHECKLIST de Requerimientos

Seguimiento del estado de implementación de cada requerimiento definido en `REQUIREMENTS.md`.

---

| # | Requerimiento | Estado | Notas |
|---|---|---|---|
| 1 | Aplicación que permita crear workflows empaquetados en `.exe` de Windows | ✅ Completado | `POST /api/workflows/{id}/build` genera el `.exe` via PyInstaller `--onefile` |
| 2 | Debe tener una interfaz web | ✅ Completado | SPA en `app/static/index.html`. Flask sirve en `http://localhost:5000` |
| 3 | Debe ser en Python | ✅ Completado | Backend Flask (Python 3.9+). El código generado también es Python puro |
| 4 | No usar librerías pesadas; usar stdlib en lo posible | ✅ Completado | Solo dos dependencias externas: `flask` (servidor) y `pyinstaller` (compilación). BD con `sqlite3` stdlib, fechas con `datetime` stdlib |
| 5 | El empaquetado debe ser ligero | ✅ Completado | PyInstaller `--onefile`. El script generado solo importa `datetime`, `time` y `os` — sin dependencias de terceros en el EXE |
| 6 | Interfaz similar a n8n pero sin todas sus funcionalidades | ✅ Completado | Canvas drag-and-drop con Drawflow 0.0.59 (vendored, ~30kb). Paleta de nodos, conexiones visuales, panel de propiedades |
| 7 | Nodos iniciales: Scheduler, Set Variables, Get Current Date UTC | ✅ Completado | `app/nodes/scheduler.py`, `app/nodes/set_variables.py`, `app/nodes/get_current_date.py` + sus contrapartes JS en `app/static/js/nodes/` |
| 8 | Base de datos SQLite | ✅ Completado | `data/main.db` (registro de workflows) + `data/{id}.db` por workflow, usando `sqlite3` de stdlib |
| 9 | Cada workflow debe tener un botón para generar el `.exe` | ✅ Completado | Botón **Generate EXE** en la barra superior. Muestra log de compilación y enlace de descarga al terminar |
| 10 | Por el momento no existen sub-workflows | ✅ Completado | No hay concepto de sub-workflow en el modelo de datos ni en el generador de código |
| 11 | La configuración de los nodos debe transformarse a código Python y compilarse con PyInstaller | ✅ Completado | `app/codegen/generator.py` convierte el grafo JSON → script `.py` autónomo via topological sort. PyInstaller compila ese script |
| 12 | Cada workflow tendrá su propio archivo SQLite | ✅ Completado | `app/db/manager.py` crea `data/{workflow_id}.db` al crear cada workflow; se elimina al borrar el workflow |

### Fase 2

| # | Requerimiento | Estado | Notas |
|---|---|---|---|
| 13 | Nodo para agregar (días, horas, minutos, segundos) a una fecha existente del workflow | ✅ Completado | `app/nodes/add_time_to_date.py` — usa `datetime.timedelta`. Registrado en `NODE_REGISTRY`. Paleta y panel de propiedades en frontend |
| 14 | Nodo para restar (días, horas, minutos, segundos) a una fecha existente del workflow | ✅ Completado | `app/nodes/subtract_time_from_date.py` — usa `datetime.timedelta` con resta. Registrado en `NODE_REGISTRY`. Paleta y panel de propiedades en frontend |
| 15 | Ejecución paralela de nodos | ✅ Completado | `_topological_waves()` en `app/codegen/generator.py` agrupa nodos independientes en waves. Cada wave multi-nodo se ejecuta con `ThreadPoolExecutor`. Paralelismo implícito basado en la topología del grafo |
| 16 | Botón Run para ejecutar workflow en el portal, con tabla de entrada/salida por nodo | ✅ Completado | Backend: `POST /api/workflows/{id}/run` ejecuta script instrumentado vía subprocess. Frontend: botón ▶ Run en topbar + panel inferior con tabla de resultados por nodo |
| 17 | Los nodos deben tener un nombre único; al crear uno con tipo ya existente agregar sufijo numérico | ✅ Completado | `generateInstanceName()` en `app/static/js/app.js` asigna el primer nombre disponible. `updateNodeTitle()` actualiza el canvas. El `instanceName` se persiste como `label` en SQLite y se restaura al cargar el grafo |

---

## Resumen

| Estado | Cantidad |
|---|---|
| ✅ Completado | 17 |
| 🔄 En progreso | 0 |
| ⏳ Pendiente | 0 |

---

_Última actualización: 2026-06-12_
