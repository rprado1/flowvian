# PLANNING — Migración Frontend: Vanilla JS → React + React Flow v11 + shadcn/ui

## Objetivo

Migrar el portal web de Vanilla JS + Drawflow a **React 18 + React Flow v11 (MIT) + shadcn/ui + Tailwind CSS**, manteniendo el backend Flask 100% intacto. La migración:

- Resuelve el bug de la tecla Delete de forma nativa (React Flow maneja `deleteKeyCode` a nivel de componente, sin depender del foco del DOM)
- Establece una base mantenible con componentes accesibles (ARIA, keyboard navigation, focus trapping vía Radix Primitives)
- Conserva la paleta visual actual mediante mapeo 1:1 de CSS variables

---

## Stack elegido

| Capa | Tecnología | Justificación |
|---|---|---|
| UI framework | **React 18** | Componentes declarativos, ecosistema amplio |
| Canvas de nodos | **React Flow v11** (`reactflow@11`, MIT) | React-nativo, reemplaza Drawflow sin fricción |
| Bundler | **Vite 5** | Rápido, genera `dist/` estático que Flask sirve directamente |
| Estilos base | **Tailwind CSS v3** | Utilidades CSS; cero JS runtime; requerido por shadcn/ui |
| Componentes UI | **shadcn/ui** | Componentes copiados como fuente (no dependencia npm); CSS vars 1:1 con paleta actual; incluye Sidebar y Resizable |
| Estado global | **React Context + useState** | Estado simple (5 variables); sin Redux ni Zustand |
| HTTP | **fetch nativo** | Conserva el helper `api()` existente |
| Lenguaje | **JavaScript (sin TypeScript)** | Velocidad de migración; TypeScript puede añadirse después |

**Backend: sin cambios.** Flask sigue sirviendo `app/static/index.html` en `/`.

---

## Por qué shadcn/ui sobre otras alternativas

| Criterio | antd | **shadcn/ui** | Chakra v3 | MUI |
|---|---|---|---|---|
| Bundle añadido (gz) | ~150 KB | **~65 KB** | ~130 KB | ~180 KB |
| Paleta dark personalizada | Token API JS | **CSS vars 1:1** | Token chain | Lucha contra ti |
| Componente Sidebar | No | **Sí** | No | No |
| Componente Resizable | No | **Sí** | No | No |
| Theming runtime | CSS-in-JS (55 KB) | **Cero** | Emotion | Emotion |
| Estética neutral | No (Ant) | **Sí** | Moderado | Material Design |

### Mapeo de CSS variables (actual → shadcn tokens)

| Variable actual | Token shadcn/ui | Valor |
|---|---|---|
| `--bg-dark` | `--background` | `#1a1a2e` |
| `--bg-panel` | `--card` | `#16213e` |
| `--bg-card` | `--popover` | `#0f3460` |
| `--accent` | `--primary` | `#e94560` |
| `--accent-green` | `--chart-1` (o custom) | `#1db954` |
| `--text` | `--foreground` | `#e0e0e0` |
| `--text-muted` | `--muted-foreground` | `#8899aa` |
| `--border` | `--border` | `#2a3a5a` |
| `--accent-hover` | `--primary/90` (Tailwind opacity) | `#c73652` |

---

## Estructura de directorios propuesta

```
workflow-exe/
├── app/
│   ├── static/
│   │   ├── index.html          ← REEMPLAZADO: solo <div id="root"> + script Vite
│   │   ├── css/
│   │   │   ├── style.css       ← ELIMINADO (Tailwind + shadcn lo reemplaza)
│   │   │   └── drawflow.min.css← ELIMINADO
│   │   ├── js/
│   │   │   ├── drawflow.min.js ← ELIMINADO
│   │   │   └── nodes/          ← ELIMINADO
│   │   └── dist/               ← NUEVO: output de `vite build` (no commitear)
│   └── ... (backend sin cambios)
├── frontend/                   ← NUEVO: código fuente React
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── index.css           ← Tailwind directives + shadcn CSS vars
│   │   ├── api.js              ← helper fetch (idéntico al actual)
│   │   ├── context/
│   │   │   └── WorkflowContext.jsx
│   │   ├── components/
│   │   │   ├── ui/             ← generado por shadcn CLI (no editar manualmente)
│   │   │   │   ├── button.jsx
│   │   │   │   ├── input.jsx
│   │   │   │   ├── select.jsx
│   │   │   │   ├── dialog.jsx
│   │   │   │   ├── toast.jsx / sonner.jsx
│   │   │   │   ├── table.jsx
│   │   │   │   ├── sidebar.jsx
│   │   │   │   └── resizable.jsx
│   │   │   ├── TopBar.jsx
│   │   │   ├── AppSidebar.jsx
│   │   │   ├── Canvas.jsx
│   │   │   ├── PropsPanel.jsx
│   │   │   ├── RunPanel.jsx
│   │   │   └── modals/
│   │   │       ├── NewWorkflowModal.jsx
│   │   │       ├── RenameModal.jsx
│   │   │       ├── DeleteModal.jsx
│   │   │       └── BuildLogModal.jsx
│   │   ├── nodes/
│   │   │   ├── index.js
│   │   │   ├── BaseNode.jsx
│   │   │   ├── SchedulerNode.jsx
│   │   │   ├── SetVariablesNode.jsx
│   │   │   ├── GetCurrentDateNode.jsx
│   │   │   ├── AddTimeToDateNode.jsx
│   │   │   └── SubtractTimeFromDateNode.jsx
│   │   └── hooks/
│   │       ├── useWorkflows.js
│   │       ├── useGraph.js
│   │       ├── useBuild.js
│   │       └── useToast.js
│   ├── index.html              ← template HTML de Vite
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
└── _docs/
    └── planning/
        └── PLANNING4.md
```

---

## Integración con Flask

### Desarrollo

```bash
# Terminal 1 — backend
python run.py

# Terminal 2 — frontend (con proxy a Flask)
cd frontend && npm run dev   # Vite en :5173, proxea /api/* → :5000
```

### Producción / uso normal

```bash
cd frontend && npm run build
# dist/ → app/static/dist/ (configurado en vite.config.js)
# Flask sirve index.html en / y dist/* como estáticos
```

### `vite.config.js`

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    outDir: '../app/static/dist',
    emptyOutDir: true,
  },
  server: {
    proxy: { '/api': 'http://localhost:5000' },
  },
});
```

### `tailwind.config.js`

```js
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        background:  'hsl(var(--background))',
        card:        'hsl(var(--card))',
        primary:     'hsl(var(--primary))',
        border:      'hsl(var(--border))',
        foreground:  'hsl(var(--foreground))',
        muted:       { foreground: 'hsl(var(--muted-foreground))' },
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
```

### `src/index.css` — CSS vars (paleta actual mapeada a shadcn tokens)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background:        222 47% 11%;   /* #1a1a2e */
    --foreground:        210 20% 88%;   /* #e0e0e0 */
    --card:              222 47%  9%;   /* #16213e */
    --card-foreground:   210 20% 88%;
    --popover:           214 75% 22%;   /* #0f3460 */
    --popover-foreground:210 20% 88%;
    --primary:           349 76% 57%;   /* #e94560 */
    --primary-foreground:0   0% 100%;
    --secondary:         214 75% 22%;
    --secondary-foreground: 210 20% 88%;
    --muted:             218 38% 18%;
    --muted-foreground:  213 20% 63%;   /* #8899aa */
    --accent:            214 75% 22%;
    --accent-foreground: 210 20% 88%;
    --destructive:       349 76% 57%;
    --destructive-foreground: 0 0% 100%;
    --border:            221 38% 25%;   /* #2a3a5a */
    --input:             221 38% 25%;
    --ring:              349 76% 57%;
    --radius:            0.5rem;
    /* Custom — no in shadcn tokens */
    --accent-green:      #1db954;
    --accent-yellow:     #f5a623;
    --node-header:       #0f3460;
    --topbar-h:          52px;
    --sidebar-w:         260px;
    --props-w:           280px;
  }
}
```

### `app/main.py` — catch-all route para SPA

```python
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def index(path):
    if path.startswith("api/") or path.startswith("static/"):
        abort(404)
    return send_from_directory(os.path.join(STATIC_DIR, "dist"), "index.html")
```

---

## Arquitectura React Flow v11

### Modelo de datos (compatible con la BD actual)

```js
// Nodo React Flow — mismos campos que en SQLite
{
  id: "3",
  type: "scheduler",
  position: { x: 100, y: 200 },
  data: {
    instanceName: "Scheduler",
    config: { interval: 60, unit: 'seconds' }
  }
}

// Edge React Flow
{
  id: "3_5_output_1_input_1",
  source: "3", target: "5",
  sourceHandle: "output_1", targetHandle: "input_1"
}
```

### Registro de nodos (`nodes/index.js`)

```js
export const nodeTypes = {
  scheduler:               SchedulerNode,
  set_variables:           SetVariablesNode,
  get_current_date_utc:    GetCurrentDateNode,
  add_time_to_date:        AddTimeToDateNode,
  subtract_time_from_date: SubtractTimeFromDateNode,
};

export const NODE_META = {
  scheduler:               { label: 'Scheduler',              icon: '⏱', inputs: 0, outputs: 1, defaultConfig: () => ({ interval: 60, unit: 'seconds' }) },
  set_variables:           { label: 'Set Variables',          icon: '📦', inputs: 1, outputs: 1, defaultConfig: () => ({ variables: [] }) },
  get_current_date_utc:    { label: 'Get Current Date UTC',   icon: '📅', inputs: 1, outputs: 1, defaultConfig: () => ({ output_var: 'current_date_utc' }) },
  add_time_to_date:        { label: 'Add Time to Date',       icon: '⏩', inputs: 1, outputs: 1, defaultConfig: () => ({ input_var: '', days: 0, hours: 0, minutes: 0, seconds: 0, output_var: 'new_date' }) },
  subtract_time_from_date: { label: 'Subtract Time from Date',icon: '⏪', inputs: 1, outputs: 1, defaultConfig: () => ({ input_var: '', days: 0, hours: 0, minutes: 0, seconds: 0, output_var: 'new_date' }) },
};
```

### Cómo React Flow resuelve el bug de Delete

```jsx
// Canvas.jsx
<ReactFlow
  nodes={nodes}
  edges={edges}
  nodeTypes={nodeTypes}
  deleteKeyCode="Delete"            // React Flow intercepta Delete nativamente
  onNodesDelete={handleNodesDelete} // cierra PropsPanel reactivamente
>
```

`onNodesDelete` recibe los nodos eliminados. El estado `selectedNodeId` se limpia en ese handler, y `PropsPanel` se cierra de forma reactiva (no necesita lógica de foco DOM).

### Solución de nombres únicos migrada al contexto

```js
// WorkflowContext.jsx
function generateInstanceName(type, currentNodes) {
  const baseName = NODE_META[type].label;
  const used = new Set(currentNodes.map(n => n.data.instanceName).filter(Boolean));
  if (!used.has(baseName)) return baseName;
  for (let n = 2; n < 9999; n++) {
    const candidate = `${baseName} ${n}`;
    if (!used.has(candidate)) return candidate;
  }
  return baseName;
}
```

### Mapeo API ↔ React Flow

**Al guardar:**
```js
const apiNodes = rfNodes.map(n => ({
  id: n.id, type: n.type,
  label:  n.data.instanceName,
  pos_x:  n.position.x, pos_y: n.position.y,
  config: n.data.config,
}));
const apiEdges = rfEdges.map(e => ({
  id: e.id,
  source_node_id: e.source, target_node_id: e.target,
  source_output:  e.sourceHandle || 'output_1',
  target_input:   e.targetHandle || 'input_1',
}));
```

**Al cargar:**
```js
const rfNodes = apiNodes.map(n => ({
  id: n.id, type: n.type,
  position: { x: n.pos_x, y: n.pos_y },
  data: {
    instanceName: n.label || NODE_META[n.type]?.label || n.type,
    config:       n.config || NODE_META[n.type]?.defaultConfig() || {},
  },
}));
const rfEdges = apiEdges.map(e => ({
  id: e.id,
  source: e.source_node_id, target: e.target_node_id,
  sourceHandle: e.source_output, targetHandle: e.target_input,
}));
```

---

## Panel de propiedades — formulario controlado

Cada nodo exporta un componente `PropsForm` con estado controlado React. Elimina el patrón `renderProps()/readProps()` (que leía el DOM) y elimina `_esc()` (React escapa HTML automáticamente).

```jsx
// nodes/SchedulerNode.jsx
export function PropsForm({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div className="prop-group">
        <label className="text-sm text-muted-foreground">Interval</label>
        <Input type="number" value={config.interval}
               onChange={e => onChange({ ...config, interval: +e.target.value })} />
      </div>
      <div className="prop-group">
        <label className="text-sm text-muted-foreground">Unit</label>
        <Select value={config.unit} onValueChange={v => onChange({ ...config, unit: v })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="seconds">Seconds</SelectItem>
            <SelectItem value="minutes">Minutes</SelectItem>
            <SelectItem value="hours">Hours</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
```

---

## Plan de tareas (orden de ejecución)

### Fase A — Scaffolding

| # | Tarea | Archivos |
|---|---|---|
| A1 | Crear `frontend/` con Vite + React: `npm create vite@latest frontend -- --template react` | `frontend/` |
| A2 | Instalar dependencias: `react`, `react-dom`, `reactflow@11`, Tailwind, PostCSS, shadcn CLI | `package.json` |
| A3 | Configurar Tailwind: `tailwind.config.js`, `postcss.config.js` | config files |
| A4 | Configurar Vite: `outDir`, alias `@`, proxy `/api` | `vite.config.js` |
| A5 | Inicializar shadcn: `npx shadcn@latest init` (modo dark, CSS vars, alias `@`) | `components.json` |
| A6 | Instalar componentes shadcn: `button input select dialog toast table sidebar resizable label` | `src/components/ui/` |
| A7 | Crear `src/index.css` con tokens CSS (paleta actual mapeada a shadcn vars) | `src/index.css` |

### Fase B — API y contexto global

| # | Tarea | Archivos |
|---|---|---|
| B1 | Migrar helper `api()` a `src/api.js` (idéntico al actual) | `src/api.js` |
| B2 | Crear `WorkflowContext.jsx`: state (`workflows`, `currentWfId`, `selectedNodeId`, `nodes`, `edges`), `generateInstanceName()` | `src/context/WorkflowContext.jsx` |
| B3 | Crear hook `useWorkflows`: list, create, rename, delete | `src/hooks/useWorkflows.js` |
| B4 | Crear hook `useGraph`: `loadGraph`, `saveGraph` con debounce 800ms | `src/hooks/useGraph.js` |
| B5 | Crear hook `useBuild`: start build, poll status cada 2s | `src/hooks/useBuild.js` |
| B6 | Crear hook `useToast`: wrapper de shadcn Sonner | `src/hooks/useToast.js` |

### Fase C — Componentes de nodos

| # | Tarea | Archivos |
|---|---|---|
| C1 | Crear `BaseNode.jsx`: estructura compartida con handles React Flow, `title-box` con icon + instanceName, `box` para preview | `src/nodes/BaseNode.jsx` |
| C2 | `SchedulerNode.jsx`: card + `PropsForm` (interval, unit) | `src/nodes/SchedulerNode.jsx` |
| C3 | `SetVariablesNode.jsx`: card + `PropsForm` (lista dinámica key/value con Add/Remove) | `src/nodes/SetVariablesNode.jsx` |
| C4 | `GetCurrentDateNode.jsx`: card + `PropsForm` (output_var) | `src/nodes/GetCurrentDateNode.jsx` |
| C5 | `AddTimeToDateNode.jsx`: card + `PropsForm` (input_var, days/hours/minutes/seconds, output_var) | `src/nodes/AddTimeToDateNode.jsx` |
| C6 | `SubtractTimeFromDateNode.jsx`: ídem con labels "subtract" | `src/nodes/SubtractTimeFromDateNode.jsx` |
| C7 | `nodes/index.js`: `nodeTypes` + `NODE_META` | `src/nodes/index.js` |

### Fase D — Componentes de UI

| # | Tarea | Archivos |
|---|---|---|
| D1 | `Canvas.jsx`: `<ReactFlow>` con `nodeTypes`, `deleteKeyCode="Delete"`, `onNodesDelete`, drag-drop desde paleta, auto-save on change | `src/components/Canvas.jsx` |
| D2 | `TopBar.jsx`: brand, nombre workflow (click → rename modal), botones Save/Preview/Run/Build usando `<Button>` shadcn | `src/components/TopBar.jsx` |
| D3 | `AppSidebar.jsx`: lista de workflows + paleta de nodos draggable usando `<Sidebar>` shadcn | `src/components/AppSidebar.jsx` |
| D4 | `PropsPanel.jsx`: panel derecho con `PropsForm` dinámico según tipo de nodo; se cierra cuando `selectedNodeId` es null | `src/components/PropsPanel.jsx` |
| D5 | `RunPanel.jsx`: tabla de trazas usando `<Table>` shadcn; panel redimensionable con `<Resizable>` shadcn | `src/components/RunPanel.jsx` |
| D6 | `NewWorkflowModal.jsx` usando `<Dialog>` shadcn | `src/components/modals/NewWorkflowModal.jsx` |
| D7 | `RenameModal.jsx` usando `<Dialog>` shadcn | `src/components/modals/RenameModal.jsx` |
| D8 | `DeleteModal.jsx` usando `<Dialog>` shadcn | `src/components/modals/DeleteModal.jsx` |
| D9 | `BuildLogModal.jsx` usando `<Dialog>` shadcn + `<pre>` para log + botón descarga | `src/components/modals/BuildLogModal.jsx` |

### Fase E — Integración y ajustes Flask

| # | Tarea | Archivos |
|---|---|---|
| E1 | `App.jsx`: componer layout con `<WorkflowProvider>`, `<Toaster>`, todos los componentes | `src/App.jsx` |
| E2 | `frontend/index.html`: template Vite mínimo (`<div id="root">`) | `frontend/index.html` |
| E3 | Actualizar `app/static/index.html`: shell mínimo que carga `dist/` | `app/static/index.html` |
| E4 | Actualizar `app/main.py`: catch-all route para SPA, servir desde `dist/` | `app/main.py` |
| E5 | `npm run build` → verificar que `app/static/dist/` se genera correctamente | build |
| E6 | `python -c "from app.main import app; print('OK')"` | verificación backend |
| E7 | Prueba manual completa (checklist) | manual |

### Fase F — Limpieza

| # | Tarea | Archivos |
|---|---|---|
| F1 | Eliminar `app/static/js/drawflow.min.js` | |
| F2 | Eliminar `app/static/js/nodes/` | |
| F3 | Eliminar `app/static/js/app.js` | |
| F4 | Eliminar `app/static/css/drawflow.min.css` | |
| F5 | Eliminar `app/static/css/style.css` | |
| F6 | Actualizar `.gitignore`: agregar `frontend/node_modules/`, `app/static/dist/` | `.gitignore` |

---

## Dependencias del `package.json`

```json
{
  "dependencies": {
    "react":              "^18.3.1",
    "react-dom":          "^18.3.1",
    "reactflow":          "^11.11.4",
    "class-variance-authority": "^0.7.1",
    "clsx":               "^2.1.1",
    "tailwind-merge":     "^2.5.4",
    "lucide-react":       "^0.468.0",
    "sonner":             "^1.7.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite":                 "^5.4.0",
    "tailwindcss":          "^3.4.17",
    "tailwindcss-animate":  "^1.0.7",
    "autoprefixer":         "^10.4.20",
    "postcss":              "^8.4.49"
  }
}
```

**Dependencias de producción: 8.** Sin TypeScript, sin linter configurado, sin test framework (consistente con el proyecto actual).

---

## Casos borde conocidos: shadcn/ui + React Flow

| Caso | Descripción | Mitigación |
|---|---|---|
| Radix `DismissableLayer` + RF click-outside | Al hacer clic en el canvas de React Flow, los dropdowns/dialogs de Radix pueden no detectarlo como "click fuera" porque React Flow llama `stopPropagation` | Pasar `onInteractOutside={e => e.preventDefault()}` solo en los modales que se abren desde el canvas; los modales de botones de topbar no se ven afectados |
| z-index de `<Dialog>` shadcn | Por defecto usa z-index alto que puede cubrir el canvas | Añadir `className="z-50"` al `DialogOverlay` para igualar con el z-index del canvas |
| `<Select>` dentro de nodos React Flow | El dropdown de shadcn Select renderiza en un portal fuera del nodo — no es problema de z-index, pero el scroll del canvas puede cerrarlo | Usar `<SelectContent position="popper"` que ancla al trigger y evita el cierre por scroll |

---

## Checklist de verificación post-migración

| # | Verificación |
|---|---|
| 1 | App carga en `http://localhost:5000` y muestra canvas vacío |
| 2 | Crear workflow → aparece en sidebar |
| 3 | Arrastrar nodo al canvas → aparece con nombre correcto |
| 4 | Arrastrar 2 nodos del mismo tipo → sufijo numérico (`Set Variables 2`) |
| 5 | Click en nodo → panel derecho se abre con formulario |
| 6 | Editar campo del panel → preview del nodo se actualiza |
| 7 | **Presionar Delete con nodo seleccionado** → nodo eliminado, panel cerrado |
| 8 | **Presionar Delete mientras se edita un input del panel** → nodo NO se elimina |
| 9 | Conectar dos nodos → arista aparece |
| 10 | Auto-save tras mover nodo → sin errores de red (DevTools Network) |
| 11 | Guardar → toast "Saved" |
| 12 | Recargar → grafo se restaura con nombres de instancia |
| 13 | Preview → modal con código Python |
| 14 | Run → tabla de resultados por nodo |
| 15 | Generate EXE → build + descarga |
| 16 | `python -c "from app.main import app; print('OK')"` → OK |

---

## Riesgos y mitigaciones

| Riesgo | Prob. | Mitigación |
|---|---|---|
| React Flow v11 + React 18 incompatibilidades | Baja | RF 11.11.x tiene soporte oficial para React 18 |
| shadcn init falla sin TypeScript | Baja | `shadcn init` acepta JS con flag `--jsx` o ajustando `jsconfig.json` |
| CSS vars en formato HSL vs hex | Media | shadcn usa `hsl(var(--x))` internamente; las vars deben ser valores HSL sin `hsl()`. La tabla de mapeo ya los convierte |
| Workflows existentes no cargan post-migración | Baja | Formato de BD no cambia; el mapeo load→RF está definido explícitamente |
| Vite genera rutas absolutas que Flask no sirve | Baja | `base: './'` en `vite.config.js` garantiza rutas relativas |
| `_run_build()` dead code en `builder.py` (bug latente) | Baja | No se toca en esta migración; se puede eliminar en una limpieza posterior |
