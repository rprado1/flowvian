# WorkflowEXE Builder

Herramienta visual para crear workflows y compilarlos como ejecutables `.exe` de Windows.

Diseña el flujo arrastrando nodos en un canvas estilo n8n, configura cada paso y genera un `.exe` autónomo con un clic.

---

## Requisitos

- Python 3.9+
- Windows (el `.exe` generado es solo para Windows)

---

## Instalación

**1. Clonar el repositorio y entrar al directorio:**

```bash
git clone <url-del-repo>
cd workflow-exe
```

**2. Crear el entorno virtual:**

```bash
python -m venv .venv
```

**3. Activar el entorno virtual:**

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat
```

**4. Instalar dependencias:**

```bash
pip install -r requirements.txt
```

---

## Uso

Con el entorno virtual activo:

```bash
python run.py
```

Abre el navegador en `http://localhost:5000`.

> Siempre ejecutar desde la raíz del proyecto con el venv activo. Si el venv no está activo, los imports de `app.*` fallarán.

---

## Desactivar el entorno virtual

```bash
deactivate
```

---

## Interfaz

### Barra superior
| Elemento | Descripción |
|---|---|
| Nombre del workflow | Clic para renombrar |
| **Preview Code** | Muestra el Python que se generará |
| **Save** | Guarda el grafo manualmente (también se guarda automáticamente) |
| **Generate EXE** | Compila el workflow a `.exe` via PyInstaller |

### Sidebar izquierdo
- Lista de workflows: crear, seleccionar, eliminar
- Paleta de nodos: arrastrar al canvas

### Panel derecho
Aparece al hacer clic en un nodo. Permite configurar sus parámetros.

---

## Nodos disponibles

### Scheduler
Ejecuta el workflow en un bucle con pausa entre iteraciones.

| Campo | Tipo | Descripción |
|---|---|---|
| Interval | número | Frecuencia de ejecución |
| Unit | seconds / minutes / hours | Unidad del intervalo |

Genera:
```python
_sleep_seconds = 60.0
while True:
    # resto del workflow
    import time
    time.sleep(_sleep_seconds)
```

### Set Variables
Asigna pares clave=valor al contexto del workflow.

| Campo | Descripción |
|---|---|
| key | Nombre de variable Python válido |
| value | Valor (se almacena como string) |

Genera:
```python
mi_variable = 'valor'
```

### Get Current Date UTC
Captura la fecha/hora UTC actual en una variable.

| Campo | Descripción |
|---|---|
| Output variable name | Nombre de la variable resultado |

Genera:
```python
from datetime import datetime, timezone
current_date_utc = datetime.now(timezone.utc)
```

---

## Generar EXE

1. Diseña el workflow y conecta los nodos
2. Haz clic en **Generate EXE**
3. Espera la compilación (puede tomar ~1 minuto la primera vez)
4. Descarga el `.exe` desde el diálogo de resultado

El ejecutable es autónomo (`--onefile`) y no requiere Python instalado en la máquina destino.

---

## Estructura del proyecto

```
workflow-exe/
├── run.py                     # Punto de entrada
├── requirements.txt           # flask, pyinstaller
├── app/
│   ├── main.py                # Flask app
│   ├── api/
│   │   ├── workflows.py       # CRUD de workflows y grafo
│   │   └── builder.py        # Validar / previsualizar / compilar / descargar
│   ├── db/
│   │   └── manager.py         # SQLite: main.db + {id}.db por workflow
│   ├── nodes/
│   │   ├── base.py            # Clase abstracta BaseNode
│   │   ├── scheduler.py
│   │   ├── set_variables.py
│   │   └── get_current_date.py
│   ├── codegen/
│   │   └── generator.py       # Topological sort + generación de código
│   └── static/                # Frontend (HTML + CSS + JS)
├── data/                      # Bases de datos SQLite (generado en runtime)
└── output/                    # Scripts .py y .exe compilados (generado en runtime)
```

---

## API REST

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/workflows/` | Lista todos los workflows |
| POST | `/api/workflows/` | Crea un workflow |
| GET | `/api/workflows/{id}` | Obtiene metadata + grafo |
| PUT | `/api/workflows/{id}` | Renombra / actualiza metadata |
| DELETE | `/api/workflows/{id}` | Elimina workflow y su BD |
| GET | `/api/workflows/{id}/graph` | Obtiene nodos y edges |
| POST | `/api/workflows/{id}/graph` | Guarda nodos y edges |
| POST | `/api/workflows/{id}/validate` | Valida sin compilar |
| POST | `/api/workflows/{id}/preview` | Retorna el código Python generado |
| POST | `/api/workflows/{id}/build` | Compila a `.exe` |
| GET | `/api/workflows/{id}/download` | Descarga el `.exe` |

---

## Agregar nuevos nodos

1. Crear `app/nodes/mi_nodo.py` extendiendo `BaseNode`:

```python
from app.nodes.base import BaseNode

class MiNodo(BaseNode):
    NODE_TYPE = "mi_nodo"

    def validate(self) -> list:
        return []  # retornar lista de errores

    def to_code(self, indent: int = 0) -> str:
        return self._indent("# mi lógica aquí", indent)
```

2. Registrar en `app/codegen/generator.py`:

```python
from app.nodes.mi_nodo import MiNodo
NODE_REGISTRY["mi_nodo"] = MiNodo
```

3. Crear `app/static/js/nodes/mi_nodo.js` con la definición visual y registrarlo en `index.html`.

---

## Base de datos

Cada workflow usa su propio archivo SQLite (`data/{id}.db`) con dos tablas:

- **nodes** — id, tipo, posición, configuración JSON
- **edges** — conexiones entre nodos

Un archivo central `data/main.db` mantiene el registro de todos los workflows.
