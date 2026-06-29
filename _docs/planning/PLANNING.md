# Planning Notes

## 2026-06-24 - Requerimiento 5 (Fase 5)

- Se agrega modal al flujo de **Generate EXE** para elegir entre:
  - `Download without debug`
  - `Download with debug`
- El frontend envía `debug: true|false` al endpoint `POST /api/workflows/{id}/build`.
- En backend se parsea el flag `debug` y se pasa al code generator.
- En modo debug, el script generado habilita logging adicional de la tabla de resultados.

### Comportamiento de debug implementado

- Para workflows con `Scheduler`, en cada iteración:
  - Se reinicia la tabla de resultados interna.
  - Se agrega una fila por nodo ejecutado con estado, `items_in`, `items_out`, y metadatos.
  - Al final de la iteración se escribe una entrada JSON (JSONL) en:
    - `<workflow_name>_debug.log`
  - El archivo queda junto al `.exe` generado.

### Compatibilidad

- Si se elige `without debug`, el flujo de compilación y descarga se mantiene igual al comportamiento existente.
- Si el workflow no tiene `Scheduler`, no hay iteraciones periódicas; por tanto no se fuerza escritura por iteración.
