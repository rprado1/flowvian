# PLANNING8 - Separar CRUD de Workspaces del Editor

## 1) Objetivo

Redisenar la navegacion para que el editor muestre solo herramientas de edicion de nodos.

Cambios objetivo:

- Quitar del editor la seccion/lista de workspaces (actualmente workflows).
- Crear una pagina independiente con tabla CRUD de workspaces.
- Al seleccionar un workspace desde esa pagina, abrir su editor dedicado.
- Dejar el sidebar izquierdo del editor exclusivamente para seleccion de nodos.

---

## 2) Alcance funcional

### Incluido

- Nueva vista/pagina de workspaces con tabla (listar, crear, renombrar, eliminar, abrir).
- Navegacion entre pagina de workspaces y pagina editor.
- Editor por workspace usando `workspaceId`/`workflowId` en ruta.
- Sidebar izquierdo del editor solo con Node Selector (busqueda, categorias, recientes, modal).
- Ajustes de TopBar para reflejar contexto de workspace actual y accion de retorno.

### No incluido (por ahora)

- Cambiar contrato de API backend (se reutilizan endpoints actuales `/api/workflows/*`).
- Multi-tenant, permisos o autenticacion avanzada.
- Rediseno visual profundo de la tabla (solo UX funcional consistente con el proyecto).

---

## 3) Estado actual resumido

- `AppSidebar` mezcla dos responsabilidades: lista CRUD de workflows + selector de nodos.
- `App.jsx` renderiza un layout unico (no hay separacion por paginas con router).
- `WorkflowContext` ya dispone de CRUD y carga de workflow, util para separar vistas.

Problema UX actual:

- El area del sidebar compite entre gestion de workspaces y catalogo de nodos.
- El editor pierde foco al tener tareas de administracion dentro de la misma vista.

---

## 4) Propuesta de arquitectura UI

### 4.1 Estructura de rutas

- `/workspaces` -> pagina de gestion (tabla CRUD).
- `/editor/:workflowId` -> pagina de edicion de un workspace.
- `/` -> redireccion a `/workspaces`.

### 4.2 Componentes principales nuevos

- `frontend/src/pages/WorkspacesPage.jsx`
  - tabla CRUD
  - acciones: crear, renombrar, eliminar, abrir
- `frontend/src/pages/EditorPage.jsx`
  - topbar del editor
  - sidebar solo nodos
  - canvas + props + run panel

### 4.3 Refactor de componentes existentes

- `AppSidebar` -> convertir en `NodeSidebar` (solo nodos).
- Reubicar UI de workflows fuera del sidebar y llevarla a `WorkspacesPage`.
- `TopBar` en editor: agregar accion "Back to Workspaces".

---

## 5) Plan de implementacion por fases

## Fase A - Navegacion base

1. Integrar router (React Router) si no existe.
2. Crear rutas `/workspaces` y `/editor/:workflowId`.
3. Redireccion inicial a `/workspaces`.

Resultado esperado:

- App con dos pantallas separadas y navegacion funcional.

## Fase B - Pagina CRUD de Workspaces

1. Implementar `WorkspacesPage` con tabla y acciones CRUD.
2. Reusar modales existentes (`NewWorkflowModal`, `RenameModal`, `DeleteModal`) o extraer variantes para uso en pagina.
3. En accion "Open", navegar a `/editor/:workflowId` y cargar workflow en contexto.

Resultado esperado:

- Gestion completa de workspaces fuera del editor.

## Fase C - Editor enfocado

1. Refactor de sidebar para dejar solo Node Selector.
2. Verificar flujo completo de agregar nodos (drag/drop y doble click).
3. Ajustar topbar para incluir retorno a `/workspaces` y nombre del workspace activo.

Resultado esperado:

- Editor limpio, enfocado solo en construccion del flujo.

## Fase D - Ajustes y validacion

1. Revisar estados vacios y errores (sin workspace cargado, id invalido, borrado desde otra vista).
2. Ejecutar `npm run build` y corregir issues.
3. Actualizar docs (`_docs/CHECKLIST.md` y/o `REQUIREMENTS.md`) si aplica.

---

## 6) Archivos candidatos a crear/modificar

### Crear

- `frontend/src/pages/WorkspacesPage.jsx`
- `frontend/src/pages/EditorPage.jsx`

### Modificar

- `frontend/src/App.jsx` (rutas y layout por pagina)
- `frontend/src/components/AppSidebar.jsx` (convertir a sidebar de nodos unicamente)
- `frontend/src/components/TopBar.jsx` (boton volver, contexto editor)
- `frontend/src/context/WorkflowContext.jsx` (helpers de carga por id desde ruta, si hiciera falta)
- `frontend/src/index.css` (ajustes de layout para nueva pantalla de tabla)

---

## 7) Criterios de aceptacion

1. En el editor no se visualiza lista/CRUD de workspaces.
2. El sidebar izquierdo del editor contiene solo seleccion de nodos.
3. Existe una pagina independiente de workspaces con CRUD funcional.
4. Al abrir un workspace desde la tabla, se entra al editor de ese workspace.
5. Navegar de vuelta a workspaces no rompe estado ni genera errores.
6. Build frontend exitoso (`npm run build`).

---

## 8) Riesgos y mitigaciones

- Riesgo: perder compatibilidad con modales actuales de CRUD.
  - Mitigacion: desacoplar modales del layout anterior y consumirlos desde la nueva pagina.

- Riesgo: estado inconsistente al entrar directo a `/editor/:id`.
  - Mitigacion: validar existencia del id; si falla, mostrar mensaje y redirigir a `/workspaces`.

- Riesgo: regresion en auto-save del editor.
  - Mitigacion: mantener `WorkflowContext` como fuente unica de estado y no duplicar logica en pagina.

---

## 9) Resultado esperado

Disponer de una experiencia separada por contexto:

- Gestion administrativa de workspaces en una pagina CRUD dedicada.
- Edicion de workflows en una pagina enfocada al canvas, con sidebar de nodos exclusivamente.

Esto mejora enfoque, escalabilidad y claridad de uso del editor a medida que crece el catalogo de nodos.
