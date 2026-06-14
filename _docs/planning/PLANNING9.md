# PLANNING9 — Semantica de salida con ramas multiples sin Merge total

## Objetivo

Definir e implementar una semantica de salida deterministica y explicita cuando existen multiples ramas terminales y no todas convergen en un nodo `merge`.

Casos a cubrir:

- N ramas sin `merge`.
- N ramas con `merge` parcial (solo algunas convergen).
- Grafo con 1 sola rama terminal (caso simple).

---

## Problema actual

Hoy la salida final puede ser ambigua porque:

- el motor termina publicando un unico `_items`,
- en ciertos casos se mezcla implicitamente el resultado de ramas terminales,
- no existe contrato formal de salida final del workflow cuando hay mas de una rama activa al final.

Esto genera resultados inesperados para usuarios que esperan separacion por rama.

---

## Decision funcional (nueva semantica)

### Regla principal

La salida final del workflow se define por nodos terminales alcanzables del grafo ejecutado.

- Un nodo terminal es un nodo sin salidas (`out_degree = 0`) dentro del subgrafo ejecutado.
- Cada nodo terminal produce una salida independiente.
- No hay merge implicito entre terminales.
- Solo los nodos `merge` hacen combinacion explicita (`append`) de sus entradas conectadas.

### Forma de salida

Se devuelve una estructura por ramas terminales:

```json
{
  "mode": "by_terminal_branch",
  "branches": {
    "<terminal_node_id>": [ ...items... ],
    "<terminal_node_id_2>": [ ...items... ]
  },
  "terminals": [
    {"id":"...", "label":"...", "type":"..."},
    {"id":"...", "label":"...", "type":"..."}
  ]
}
```

Notas:

- Si hay un solo terminal, `branches` tendra 1 entrada.
- Para compatibilidad, puede mantenerse `legacy_items` como arreglo plano (opcional, ver compatibilidad).

---

## Alcance tecnico

### 1) Backend — `app/codegen/generator.py`

#### 1.1 Estado interno por nodo

Conservar/enforzar mapa por nodo:

- `_node_items[node_id] = items_out del nodo`

#### 1.2 Calculo de terminales finales

- Construir terminales reales del subgrafo ejecutado.
- No colapsar terminales en un unico `_items` plano como contrato principal.
- Mantener `_items` solo como compatibilidad interna si hace falta.

#### 1.3 Emision de resultado estructurado

En `generate_run_script()`:

- construir `_workflow_output` al final con:
  - `mode`,
  - `branches` por terminal,
  - `terminals` (id/label/type).
- incluir este objeto en trazas o imprimirlo como salida final principal.

En `generate_script()` (runtime normal):

- decidir si imprime:
  - solo `branches` (nuevo contrato), o
  - `legacy_items` + `branches` (modo transicion).

---

### 2) Backend API — `app/api/builder.py`

#### 2.1 Endpoint `POST /<workflow_id>/run`

- agregar campo nuevo en response:
  - `final_output` (estructura por ramas terminales).
- mantener `output` textual por compatibilidad si aplica.
- si no hay terminales validos, devolver `branches: {}`.

#### 2.2 Contrato de respuesta

Ejemplo:

```json
{
  "traces": [...],
  "output": "...",
  "final_output": {
    "mode": "by_terminal_branch",
    "branches": {
      "node_a": [{"a":"1"}],
      "node_b": [{"b":"2"}]
    },
    "terminals": [
      {"id":"node_a","label":"A","type":"set_variables"},
      {"id":"node_b","label":"B","type":"set_variables"}
    ]
  }
}
```

---

### 3) Frontend — visualizacion de resultados

#### 3.1 `frontend/src/components/RunPanel.jsx`

- mostrar bloque "Final Output" usando `final_output.branches`.
- mantener tabla de trazas actual.
- si hay una sola rama terminal, mostrarla igual como branch unica (sin aplanar).

#### 3.2 UX

- Etiquetar claramente que la salida final es por rama terminal.
- Evitar interpretar salida plana como merge implicito.

---

## Compatibilidad y migracion

### Opcion recomendada (transicion suave)

- Fase 1:
  - introducir `final_output` estructurado,
  - conservar `output`/`legacy_items`.
- Fase 2:
  - documentar deprecacion de salida plana como fuente principal.

---

## Validaciones complementarias

- Si el usuario espera una sola salida, debe usar `merge` explicito.
- Opcional: advertir cuando hay mas de un terminal:
  - "Workflow ends with multiple terminal branches; output will be returned per branch."

---

## Pruebas

### A. Unitarias / smoke backend

1. 3 ramas sin merge -> `final_output.branches` con 3 entradas.
2. 3 ramas, merge de 2 -> `final_output.branches` incluye:
   - rama del merge (combinada),
   - rama no conectada al merge (separada).
3. Flujo lineal simple -> una sola branch.
4. Merge parcial + nodo downstream -> solo terminales reales.

### B. API run

- `POST /run` devuelve `final_output` consistente con terminales.
- No mezcla automatica de ramas no convergidas.

### C. Frontend

- RunPanel muestra ramas separadas correctamente.
- No confusion entre trazas intermedias y salida final.

---

## Criterio de aceptacion

- Existe definicion formal de salida final basada en terminales.
- Las ramas no convergidas por `merge` se mantienen separadas en salida.
- `merge` sigue siendo el unico mecanismo de combinacion explicita.
- `run` devuelve `final_output` estructurado y consistente.
- UI muestra claramente salida por rama terminal sin ambiguedad.
