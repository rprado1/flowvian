# PLANNING — Requerimiento #6 Fase 2: Cerrar panel al eliminar nodo con tecla Delete

## Objetivo

Cuando un nodo está seleccionado (panel de propiedades abierto) y el usuario pulsa la tecla **Delete**, el nodo se elimina pero el panel de configuración queda abierto y bloqueado. El comportamiento esperado es que el nodo se elimine y el panel se cierre automáticamente.

---

## Diagnóstico del bug (revisado tras investigación profunda)

### Causa raíz real: el evento `keydown` nunca llega a Drawflow

El diagnóstico anterior era incorrecto. La investigación del código fuente de Drawflow reveló que el problema **no** es que `nodeRemoved` se dispare sin limpiar estado — es que el `keydown` de la tecla Delete **nunca llega** al handler de Drawflow en absoluto.

#### Por qué no llega

Drawflow registra su handler de teclado así en `start()`:

```js
this.container.tabIndex = 0;   // hace #drawflow focusable
this.container.addEventListener("keydown", this.key.bind(this));
```

El listener vive **exclusivamente en `#drawflow`**. Para que dispare, `#drawflow` debe estar **enfocado** (`document.activeElement === #drawflow`) en el momento en que el usuario presiona Delete.

El flujo que rompe el foco:

```
1. Usuario hace clic en el nodo → #drawflow recibe el clic → #drawflow tiene el foco ✅
2. selectNode() dispara → openPropsPanel() inyecta <input>/<select> en #props-body
3. El panel se muestra con campos de formulario visibles
4. El usuario (inevitablemente) hace clic en algún campo del panel para configurar el nodo
   → el <input> recibe el foco → #drawflow pierde el foco ❌
5. Usuario presiona Delete
   → keydown se dispara sobre el <input> enfocado (dentro de #props-panel)
   → el evento NUNCA llega a #drawflow
   → Drawflow no ve la tecla → no elimina el nodo → panel permanece abierto
```

Incluso si el usuario no hace clic en un input, existe un segundo guard dentro del propio handler de Drawflow que bloquea la eliminación:

```js
// drawflow.min.js — key()
("Delete" === e.key) && (
    null != this.node_selected &&
    "INPUT"    !== this.first_click.tagName &&  // ← si el último clic fue en un <input>
    "TEXTAREA" !== this.first_click.tagName &&  //   del nodo, esto bloquea
    this.removeNodeId(this.node_selected.id)
)
```

`this.first_click` se establece en el `mousedown` del **último clic dentro de `#drawflow`**. Si el usuario hizo clic en un campo de texto dentro de la tarjeta del nodo, `first_click.tagName === "INPUT"` y la eliminación queda bloqueada aunque el foco siga en `#drawflow`.

### Resumen de causas

| # | Causa | Efecto |
|---|---|---|
| 1 | Al abrir el panel de props, el usuario interactúa con `<input>` → foco sale de `#drawflow` | Delete no llega al handler de Drawflow → **nodo no se elimina** |
| 2 | Guard `first_click.tagName !== "INPUT"` en Drawflow | Bloquea eliminación si el último clic dentro del canvas fue en un input del nodo |

### Estado de la implementación anterior (`editor.node_selected = null`)

El cambio implementado en la iteración anterior (limpiar `editor.node_selected` en `nodeRemoved`) es **correcto y necesario** para el caso del botón `×`, pero no resuelve este bug porque el `keydown` nunca llega a Drawflow en primer lugar. Ese cambio puede quedar como está (es beneficioso para la limpieza de estado).

---

## Diseño de la solución

### Principio

En lugar de depender del handler nativo de teclado de Drawflow (que requiere foco en `#drawflow`), la aplicación implementa su **propio handler `keydown` a nivel de `document`** que detecta Delete cuando hay un nodo seleccionado y ejecuta la eliminación directamente llamando a la API de Drawflow.

Esto es más robusto que intentar gestionar el foco porque:
- No requiere que el usuario nunca interactúe con los inputs del panel.
- Funciona independientemente de `first_click.tagName`.
- Es el patrón estándar para atajos de teclado globales en SPAs.

### Solución

#### Paso 1 — Handler `keydown` global en `document`

Agregar un listener en `document` que capture Delete cuando:
1. Hay un nodo seleccionado (`selectedNodeId !== null`).
2. El foco activo **no** está en un `<input>`, `<textarea>`, o elemento `contenteditable` (para no interceptar Delete mientras el usuario edita texto en un modal u otro campo).
3. No hay ningún modal abierto.

```js
document.addEventListener('keydown', e => {
    if (e.key !== 'Delete') return;
    // No actuar si el foco está en un campo de texto editable
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' ||
        document.activeElement?.isContentEditable) return;
    // No actuar si hay un modal abierto
    if (document.querySelector('.modal-backdrop:not(.hidden)')) return;
    // Si hay un nodo seleccionado, eliminarlo
    if (selectedNodeId !== null) {
        e.preventDefault();
        editor.removeNodeId('node-' + selectedNodeId);
    }
});
```

**Nota sobre `editor.removeNodeId`:** Drawflow expone este método públicamente. Recibe el id con prefijo `"node-"` (ej. `"node-3"`). Al llamarlo, Drawflow dispara `nodeRemoved` normalmente, por lo que toda la lógica de limpieza ya existente (`delete nodeConfigs[id]`, `editor.node_selected = null`, `deselectNode()`, `scheduleSave()`) se ejecuta sin duplicar código.

#### Paso 2 — Restituir foco a `#drawflow` al abrir el panel (mejora de UX, opcional pero recomendada)

Al abrir el panel de propiedades, devolver el foco a `#drawflow` para que el handler nativo de Drawflow también funcione como respaldo cuando el usuario nunca toca los inputs del panel:

```js
function openPropsPanel(title, html) {
    document.getElementById('props-title').textContent = title;
    document.getElementById('props-body').innerHTML = html;
    document.getElementById('props-panel').classList.remove('hidden');
    // Devolver foco al canvas para que Delete nativo de Drawflow también funcione
    document.getElementById('drawflow')?.focus({ preventScroll: true });
}
```

Esto no impide que el usuario haga clic en los inputs del panel — simplemente garantiza que en el momento de abrir el panel, el foco está en el lugar correcto. El handler global del Paso 1 es el seguro principal.

---

## Archivos a modificar

| Archivo | Tipo de cambio | Descripción |
|---|---|---|
| `app/static/js/app.js` | Modificación | Agregar handler `keydown` global en `document` dentro de `initEditor()` |
| `app/static/js/app.js` | Modificación | Agregar `.focus()` al final de `openPropsPanel()` |

**Total: 1 archivo, 2 bloques de código modificados.**

---

## Cambios detallados

### 1. En `initEditor()` — nuevo listener global de teclado

Agregar al final del cuerpo de `initEditor()`, después de los listeners de Drawflow:

```js
// Global keyboard shortcut: Delete removes the selected node from anywhere
document.addEventListener('keydown', e => {
    if (e.key !== 'Delete') return;
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' ||
        document.activeElement?.isContentEditable) return;
    if (document.querySelector('.modal-backdrop:not(.hidden)')) return;
    if (selectedNodeId !== null) {
        e.preventDefault();
        editor.removeNodeId('node-' + selectedNodeId);
    }
});
```

### 2. En `openPropsPanel()` — devolver foco al canvas

```js
function openPropsPanel(title, html) {
    document.getElementById('props-title').textContent = title;
    document.getElementById('props-body').innerHTML = html;
    document.getElementById('props-panel').classList.remove('hidden');
    document.getElementById('drawflow')?.focus({ preventScroll: true });
}
```

---

## Casos borde a considerar

| Caso | Comportamiento esperado |
|---|---|
| Delete con nodo seleccionado y foco en el panel de props | Handler global intercepta → nodo eliminado, panel cerrado ✅ |
| Delete con nodo seleccionado y foco en `#drawflow` | Handler nativo de Drawflow Y handler global ambos podrían disparar. El handler global llama `removeNodeId` → `nodeRemoved` dispara. El handler de Drawflow también puede llamar `removeNodeId` sobre el mismo nodo — pero Drawflow hace `delete data[id]` que sobre un id ya borrado es inofensivo. Se añade guard `if (selectedNodeId !== null)` antes de llamar para evitar doble ejecución |
| Delete mientras se escribe en un `<input>` del panel (nombre, intervalo, etc.) | Guard `tag === 'INPUT'` bloquea el handler global → el usuario puede borrar texto normalmente ✅ |
| Delete con un modal abierto (nuevo workflow, renombrar, confirmar borrar) | Guard de modal bloquea el handler global → Delete no elimina nodo ✅ |
| Delete sin ningún nodo seleccionado | `selectedNodeId === null` → handler global no actúa ✅ |
| Eliminación vía botón `×` de Drawflow | No pasa por el handler global; `nodeRemoved` ya limpia el estado ✅ |
| El handler global y el nativo de Drawflow disparan al mismo tiempo | `removeNodeId` sobre id ya eliminado: Drawflow busca el elemento DOM que ya no existe → el `querySelector` retorna `null` → Drawflow lo ignora silenciosamente. No hay error visible |

---

## Verificación

1. Crear un nodo. Hacer clic en él → panel se abre.
2. **Sin tocar ningún input del panel**, presionar Delete → nodo eliminado, panel cerrado.
3. Crear un nodo. Hacer clic en él → panel se abre. **Hacer clic en un input del panel** (ej. cambiar el intervalo del scheduler). Presionar Delete → nodo eliminado, panel cerrado.
4. Crear un nodo. Hacer clic en él. Abrir modal de nuevo workflow. Presionar Delete → nodo **no** se elimina (modal activo).
5. Crear un nodo. Hacer clic en él. Hacer clic en el `×` del panel (sin Delete) → panel se cierra, nodo permanece.
6. Crear un nodo. Eliminarlo con el botón `×` del nodo en Drawflow → sin regresión.
7. Presionar Delete sin nodo seleccionado → sin efecto.
