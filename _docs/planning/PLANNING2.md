# PLANNING — Requerimiento #5 Fase 2: Nombres Únicos de Nodos

## Objetivo

Los nodos deben tener un **nombre único** dentro de cada workflow. Al crear un nodo, si ya existe otro nodo del mismo tipo, se le agrega un **sufijo numérico** automático (ej. `Scheduler`, `Set Variables 2`, `Set Variables 3`). El nombre debe ser visible en el canvas y persistido en base de datos.

---

## Estado actual (diagnóstico)

| Aspecto | Estado actual |
|---|---|
| Campo `label` en BD (`nodes` table) | Siempre igual al `type` (ej. `"set_variables"`) |
| Nombre visible en el canvas | HTML estático generado por `def.html()` en cada nodo JS — no usa `label` |
| Lógica de deduplicación | **Inexistente** |
| `label` en `saveGraph()` (`app.js`) | `label: n.name` donde `n.name` = tipo Drawflow (siempre el tipo, nunca un nombre personalizado) |
| `label` en la UI de resultados Run | `tr.label` mostrado en la tabla de trazas — actualmente muestra el tipo raw |
| Nombres legibles por tipo | Definidos en `def.label` del objeto JS (ej. `"Scheduler"`, `"Set Variables"`) — solo se usan como título del panel de propiedades, nunca se persisten por instancia |

### Raíz del problema

1. No existe un campo de nombre por **instancia** de nodo — solo existe `type` y `label` (que es igual al tipo).
2. El HTML del nodo en el canvas es **estático** (generado en `def.html()` una sola vez) — no refleja el nombre de instancia.
3. `saveGraph()` no toma el nombre de instancia del `nodeConfigs`, sino el nombre interno de Drawflow (`n.name`).

---

## Diseño de la solución

### Principios

- El nombre de instancia se almacena en **`nodeConfigs[nodeId].instanceName`** (campo nuevo en el config de cada nodo).
- El campo `label` en la base de datos pasa a contener el **nombre de instancia** (ej. `"Set Variables 2"`), no el tipo.
- El título visible en el canvas del nodo se actualiza dinámicamente para reflejar `instanceName`.
- La lógica de deduplicación vive **exclusivamente en el frontend** (función `generateInstanceName(type)`).
- No se modifica el esquema SQLite (el campo `label` ya existe y acepta cualquier string).

### Formato del nombre único

```
<NombreLegible>           → primera instancia  (sin sufijo)
<NombreLegible> 2         → segunda instancia
<NombreLegible> 3         → tercera instancia
...
```

Ejemplos:
- `Scheduler` (solo puede haber uno, pero aplica la lógica igual)
- `Set Variables`, `Set Variables 2`, `Set Variables 3`
- `Get Current Date UTC`, `Get Current Date UTC 2`

El nombre legible base proviene de `NODE_DEFS[type].label` (ej. `"Set Variables"`).

---

## Cambios necesarios

### 1. Frontend: `app/static/js/app.js`

#### 1.1 Nueva función `generateInstanceName(type)`

Responsabilidad: recorrer todos los nodos existentes en `nodeConfigs`, contar cuántas instancias del mismo tipo ya tienen un `instanceName` asignado, y devolver el siguiente nombre disponible.

```
generateInstanceName("set_variables")
  → lee nodeConfigs en busca de instanceName que empiece con "Set Variables"
  → si no hay ninguno → retorna "Set Variables"
  → si hay uno ("Set Variables") → retorna "Set Variables 2"
  → si hay dos ("Set Variables", "Set Variables 2") → retorna "Set Variables 3"
```

Lógica interna:
1. Obtener `baseName = NODE_DEFS[type].label` (ej. `"Set Variables"`).
2. Recolectar todos los `instanceName` de los configs existentes en `nodeConfigs`.
3. Buscar el menor entero positivo `n` tal que `"<baseName> n"` (o `baseName` para n=1) no esté en uso.
4. Retornar el nombre encontrado.

#### 1.2 Modificar `addNode(type, x, y)`

- Después de obtener `config = def.defaultConfig()`, llamar `config.instanceName = generateInstanceName(type)`.
- Después de registrar `nodeConfigs[nodeId] = config`, actualizar el título del nodo en el canvas.

#### 1.3 Nueva función `updateNodeTitle(nodeId, instanceName)`

Responsabilidad: encontrar el elemento DOM del nodo en Drawflow y actualizar el texto del título (`.title-box`) con el `instanceName`.

- Selector: `#node-${nodeId} .title-box` (Drawflow crea el nodo con id `node-<id>`).
- Reemplaza solo el texto de nombre, preserva el icono (ej. `⏱`).

#### 1.4 Modificar `saveGraph()`

Actualmente: `label: n.name` (siempre el tipo Drawflow).  
Cambio: `label: (nodeConfigs[id]?.instanceName) || NODE_DEFS[n.name]?.label || n.name`.

Esto garantiza que la BD reciba el nombre de instancia real.

#### 1.5 Modificar `loadGraph()`

Al cargar nodos desde la BD:
- Si `n.label` existe y no es igual al tipo puro, usarlo como `instanceName` y almacenarlo en `nodeConfigs[dfId].instanceName = n.label`.
- Llamar `updateNodeTitle(dfId, n.label)` después de que Drawflow haya pintado el nodo (usar `setTimeout(..., 0)` si Drawflow renderiza de forma asíncrona).

#### 1.6 Evitar conflictos al cargar (regenerar nombres si es necesario)

Cuando `loadGraph()` restaura los nodos desde la BD, los `instanceName` ya están guardados — no se regeneran. `generateInstanceName` solo se invoca al **crear** un nodo nuevo.

---

### 2. Frontend: `app/static/js/nodes/*.js` (los 5 archivos de nodos)

#### 2.1 Modificar `html()` en cada definición de nodo

Actualmente el `html()` incluye el nombre hardcodeado en el `title-box`:
```js
html() {
    return `<div class="title-box"><span>${this.icon}</span> ${this.label}</div>...`;
}
```

El `title-box` debe mantener el nombre del tipo como valor inicial (correcto para la primera instancia). El nombre se actualizará dinámicamente vía `updateNodeTitle` inmediatamente después de la creación. No se requiere cambio en `html()` para el flujo de creación.

**Sin cambios requeridos** en los archivos de nodos — `updateNodeTitle` sobrescribe el contenido del `.title-box` post-renderizado.

---

### 3. Frontend: `app/static/css/style.css` (opcional)

No se requieren cambios de estilo. El `title-box` ya tiene estilos aplicados. Si el nombre de instancia es largo (ej. `"Get Current Date UTC 3"`), podría requerirse `text-overflow: ellipsis` — evaluarlo visualmente durante la implementación.

---

### 4. Backend: sin cambios

- Esquema SQLite: el campo `label TEXT NOT NULL` ya soporta el nombre de instancia — **no se modifica**.
- `save_workflow_graph()` en `app/db/manager.py`: ya persiste el `label` recibido — **no se modifica**.
- `get_workflow_graph()` en `app/db/manager.py`: ya retorna el `label` — **no se modifica**.
- `app/codegen/generator.py`: el campo `label` ya se usa en mensajes de error y trazas de ejecución — **se beneficia automáticamente** al recibir el nombre de instancia.
- `app/api/`: ningún endpoint requiere cambio.

---

## Flujo completo post-implementación

### Crear un nodo (drag & drop)

```
Usuario arrastra "Set Variables" al canvas
  → addNode("set_variables", x, y)
    → config = SetVariablesNode.defaultConfig()     // { variables: [] }
    → config.instanceName = generateInstanceName("set_variables")
       // examina nodeConfigs → retorna "Set Variables" (si es el 1ro)
       //                     → retorna "Set Variables 2" (si hay uno)
    → editor.addNode(...)  // Drawflow pinta el nodo con HTML estático
    → nodeConfigs[nodeId] = config
    → updateNodeTitle(nodeId, config.instanceName)
       // actualiza el DOM: #node-X .title-box → "⚙ Set Variables 2"
    → scheduleSave()
```

### Guardar el grafo

```
saveGraph()
  → por cada nodo: label = nodeConfigs[id].instanceName || def.label || type
  → POST /api/workflows/{id}/graph con label correcto
  → BD almacena: { type: "set_variables", label: "Set Variables 2", ... }
```

### Cargar el grafo

```
loadGraph()
  → GET /api/workflows/{id}/graph
  → por cada nodo n del servidor:
      dfId = editor.addNode(n.type, ...)
      nodeConfigs[dfId] = { ...n.config, instanceName: n.label }
      updateNodeTitle(dfId, n.label)   // restaura el nombre de instancia en el canvas
```

### Ejecución (Run) y generación de EXE

El campo `label` en las trazas y en mensajes de error ahora mostrará `"Set Variables 2"` en lugar de `"set_variables"` — mejora automática sin cambios adicionales.

---

## Archivos a modificar

| Archivo | Tipo de cambio | Descripción |
|---|---|---|
| `app/static/js/app.js` | Modificación | Agregar `generateInstanceName()`, `updateNodeTitle()`, modificar `addNode()`, `saveGraph()`, `loadGraph()` |

**Total: 1 archivo modificado.**

---

## Casos borde a considerar

| Caso | Comportamiento esperado |
|---|---|
| Primer nodo de un tipo | Nombre sin sufijo: `"Set Variables"` |
| Segundo nodo del mismo tipo | Nombre con sufijo: `"Set Variables 2"` |
| Eliminar el nodo `"Set Variables 2"` y crear uno nuevo | El nuevo toma el primer nombre disponible → `"Set Variables 2"` (rellena el hueco) |
| Cargar un grafo guardado antes de esta feature | `label` en BD es el tipo raw (ej. `"set_variables"`). Al cargar, `updateNodeTitle` lo mostraría como `"set_variables"`. Mitigación: en `loadGraph()`, si `n.label === n.type`, usar `NODE_DEFS[n.type]?.label` como fallback |
| Workflow con un solo nodo por tipo | El único nodo no lleva sufijo numérico |
| Scheduler (máximo 1 por workflow) | Nombre siempre `"Scheduler"` (sin sufijo, la validación del backend ya impide >1) |

---

## Verificación

1. Agregar 3 nodos `Set Variables` al canvas → deben mostrarse como `Set Variables`, `Set Variables 2`, `Set Variables 3`.
2. Guardar el workflow → recargar la página → los nombres deben restaurarse correctamente.
3. Eliminar `Set Variables 2` → agregar uno nuevo → debe llamarse `Set Variables 2`.
4. Ejecutar el workflow (Run) → la tabla de resultados debe mostrar los nombres de instancia.
5. Generar EXE → los mensajes de validación deben usar los nombres de instancia.
