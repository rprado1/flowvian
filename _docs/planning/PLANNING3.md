# PLANNING — Requerimiento #6 Fase 2: Cerrar panel al eliminar nodo con tecla Delete

## Objetivo

Cuando un nodo está seleccionado (panel de propiedades abierto) y el usuario pulsa la tecla **Delete**, el nodo se elimina pero el panel de configuración queda abierto y bloqueado (no responde al botón de cerrar). El comportamiento esperado es que el panel se cierre automáticamente y el estado de la aplicación quede limpio.

---

## Diagnóstico del bug

### Causa raíz

Drawflow tiene **dos rutas distintas** para eliminar un nodo, y se comportan diferente respecto a los eventos que disparan:

| Ruta | Eventos disparados | `node_selected` interno limpiado |
|---|---|---|
| Botón `×` en el nodo (UI de Drawflow) | `nodeRemoved` + `nodeUnselected` | Sí (`null`) |
| Tecla **Delete** (handler nativo de Drawflow) | Solo `nodeRemoved` | **No** (queda apuntando al DOM eliminado) |

El handler de la tecla Delete en Drawflow (`drawflow.min.js`) llama directamente a `removeNodeId()` sin limpiar `this.node_selected` ni disparar `nodeUnselected`:

```js
// Drawflow key() — ruta con Delete key
("Delete" === e.key) && (
    null != this.node_selected && this.removeNodeId(this.node_selected.id),
    // ← node_selected NUNCA se pone a null aquí
    // ← nodeUnselected NUNCA se dispara aquí
)
```

### Estado sucio post-Delete

Después de pulsar Delete sobre un nodo seleccionado:

| Variable | Estado esperado | Estado real |
|---|---|---|
| `app.js: selectedNodeId` | `null` | `null` ✅ (corregido por `deselectNode()` vía `nodeRemoved`) |
| Panel de propiedades visible | oculto | **visible** ❌ |
| `editor.node_selected` (interno Drawflow) | `null` | **ref a DOM eliminado** ❌ |
| `nodeConfigs[id]` del nodo borrado | eliminado | **huerfano en memoria** ⚠️ |

### ¿Por qué el panel queda bloqueado?

El handler actual de `nodeRemoved` en `app.js` es:

```js
editor.on('nodeRemoved', () => { scheduleSave(); deselectNode(); });
```

`deselectNode()` llama a `closePropsPanel()`, que debería ocultar el panel. Sin embargo, el panel **sí se cierra** en la mayoría de casos. Lo que el usuario reporta como "bloqueado" es el siguiente escenario de carrera:

1. El usuario pulsa Delete.
2. Drawflow elimina el nodo del DOM y dispara `nodeRemoved`.
3. `deselectNode()` → `closePropsPanel()` se ejecuta → panel se oculta. ✅
4. **Pero** `editor.node_selected` sigue apuntando al elemento DOM eliminado.
5. Cuando el usuario intenta hacer **clic en el canvas** después de la eliminación, Drawflow's `mousedown` handler ejecuta `this.node_selected.classList.remove("selected")` sobre el elemento fantasma.
6. Drawflow puede re-disparar estados internos inconsistentes, causando que el panel vuelva a abrirse o que el botón `×` del panel no funcione (porque `deselectNode()` verifica `selectedNodeId !== null` antes de limpiar — si por alguna re-entrada llega a ser no-null, el ciclo se rompe).

### Problema secundario: `nodeConfigs` con entradas huérfanas

Cuando se elimina un nodo, su entrada en `nodeConfigs` nunca se borra. Esto no causa un bug visible inmediato porque `saveGraph()` toma los nodos de `editor.export()` (que ya no incluye el nodo borrado), pero acumula basura en memoria durante la sesión.

---

## Diseño de la solución

### Principio

Interceptar el evento `nodeRemoved` para ejecutar **limpieza completa de estado**, incluyendo:

1. Cerrar el panel de propiedades.
2. Limpiar `selectedNodeId`.
3. Limpiar la entrada huérfana de `nodeConfigs`.
4. Forzar la limpieza de `editor.node_selected` dentro de Drawflow.

Todo esto ya ocurre **parcialmente** en el handler existente de `nodeRemoved`. El problema es el punto 4: `editor.node_selected` no se limpia desde fuera de Drawflow.

### Solución propuesta

#### Opción A — Limpiar `editor.node_selected` directamente (recomendada)

Modificar el handler `nodeRemoved` en `app.js` para, además de llamar a `deselectNode()`, forzar `editor.node_selected = null` después de la eliminación.

Drawflow expone `node_selected` como propiedad pública del objeto `editor`. Asignarle `null` replica exactamente lo que hace el botón `×` interno, sin necesidad de modificar el vendor.

```js
// Antes
editor.on('nodeRemoved', () => { scheduleSave(); deselectNode(); });

// Después
editor.on('nodeRemoved', id => {
    delete nodeConfigs[id];          // limpiar config huérfana
    editor.node_selected = null;     // limpiar referencia interna de Drawflow
    scheduleSave();
    deselectNode();
});
```

**Ventajas:**
- Cambio mínimo (1 línea de código de producción).
- No modifica el vendor.
- Resuelve ambos problemas: el panel y la referencia fantasma.
- Idempotente: si el nodo ya fue eliminado vía botón `×` (donde `node_selected` ya es null), asignarlo a null de nuevo es inofensivo.

**Riesgos:** Ninguno. `node_selected` es una propiedad pública y Drawflow la consulta antes de usarla (`null != this.node_selected && ...`).

#### Opción B — Modificar `deselectNode()` para ser más agresiva

Añadir la limpieza de Drawflow dentro de `deselectNode()`:

```js
function deselectNode() {
    if (selectedNodeId !== null) {
        saveCurrentProps();
    }
    selectedNodeId = null;
    editor.node_selected = null;     // nueva línea
    closePropsPanel();
}
```

**Ventajas:** Centraliza toda la lógica de "deselección" en un solo lugar.  
**Desventaja:** `deselectNode()` se llama también desde otros contextos donde `editor` podría no estar inicializado, aunque en la práctica siempre lo está durante el ciclo de vida de la app.

**Opción elegida: Opción A** — más localizada, no afecta otros flujos.

---

## Cambios necesarios

### 1. `app/static/js/app.js`

**Una sola línea cambia** en el handler `nodeRemoved`:

```js
// Línea actual (~107):
editor.on('nodeRemoved',  () => { scheduleSave(); deselectNode(); });

// Línea nueva:
editor.on('nodeRemoved', id => {
    delete nodeConfigs[id];
    editor.node_selected = null;
    scheduleSave();
    deselectNode();
});
```

**Detalle de cada línea añadida:**

| Línea | Propósito |
|---|---|
| `delete nodeConfigs[id]` | Elimina la entrada huérfana. El parámetro `id` que Drawflow pasa al evento es el id del nodo eliminado (entero como string, igual a la clave en `nodeConfigs`) |
| `editor.node_selected = null` | Limpia la referencia interna de Drawflow al DOM eliminado, evitando errores en futuros eventos de mouse |
| `scheduleSave()` | Sin cambio — persiste el grafo actualizado |
| `deselectNode()` | Sin cambio — limpia `selectedNodeId` y cierra el panel |

---

## Archivos a modificar

| Archivo | Tipo de cambio | Descripción |
|---|---|---|
| `app/static/js/app.js` | Modificación | Ampliar el handler `nodeRemoved` con limpieza de `nodeConfigs` y `editor.node_selected` |

**Total: 1 archivo modificado, 3 líneas cambiadas.**

---

## Casos borde a considerar

| Caso | Comportamiento esperado |
|---|---|
| Nodo eliminado con tecla Delete mientras panel abierto | Panel se cierra automáticamente, estado limpio |
| Nodo eliminado con botón `×` de Drawflow mientras panel abierto | Panel se cierra (ya funcionaba), sin regresión |
| Nodo eliminado sin estar seleccionado | `deselectNode()` llama a `saveCurrentProps()` que retorna temprano (guard `selectedNodeId === null`). Panel ya estaba cerrado — sin efecto |
| Múltiples nodos eliminados rápidamente (si fuera posible) | Cada `nodeRemoved` limpia su `id` de `nodeConfigs` independientemente |
| `nodeConfigs[id]` ya no existe al disparar `nodeRemoved` | `delete` sobre clave inexistente es inofensivo en JS |
| Eliminar un nodo que no estaba en `nodeConfigs` | `delete` sobre clave inexistente es inofensivo en JS |

---

## Verificación

1. Crear un workflow con al menos 2 nodos.
2. Hacer clic en un nodo → verificar que el panel de propiedades se abre.
3. Pulsar la tecla **Delete** → verificar que:
   - El nodo desaparece del canvas.
   - El panel de propiedades se cierra automáticamente.
   - El botón `×` del panel no queda bloqueado (aunque ya no es visible).
4. Hacer clic en otro nodo → verificar que el panel se abre correctamente (sin estado sucio del nodo anterior).
5. Eliminar un nodo con el botón `×` de Drawflow (mientras está seleccionado) → verificar que el comportamiento no cambió (sin regresión).
6. Eliminar un nodo **sin** seleccionarlo → verificar que el canvas y el estado son correctos.
