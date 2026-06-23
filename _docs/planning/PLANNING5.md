# Plan de Implementacion - Exportar e Importar Plantillas de Workflow

## Estado

Documento de planificacion. **No contiene implementacion**.

## Objetivo

Agregar una forma simple y segura de **exportar** e **importar** la plantilla de un workflow para reutilizar estructuras entre proyectos/ambientes.

El usuario debe poder:

- Exportar un workflow actual a un archivo de plantilla.
- Importar una plantilla para crear un nuevo workflow.
- Validar la plantilla antes de guardarla.
- Recibir errores claros si la plantilla es invalida o incompatible.

## Alcance

Incluye:

- Backend: endpoints para exportar e importar plantillas.
- Formato JSON versionado de plantilla.
- Frontend: acciones de UI para Export/Import.
- Validaciones de integridad (nodos, edges, tipos, config minima).
- Sanitizacion basica para evitar campos runtime no deseados.

No incluye (esta fase):

- Marketplace/catalogo de plantillas.
- Plantillas remotas por URL.
- Versionado avanzado con migraciones complejas multi-release.

## Reglas Funcionales

### 1) Exportar plantilla

- La exportacion toma un `workflow_id` existente.
- Genera un JSON descargable con metadatos y grafo.
- No debe incluir datos de ejecucion (logs, outputs temporales, estados UI efimeros).
- Debe preservar:
  - nombre de workflow (opcional en metadatos de plantilla)
  - lista de nodos (tipo, label, config)
  - lista de edges (source/target/handles)

### 2) Importar plantilla

- El usuario selecciona un archivo `.json`.
- El backend valida estructura y contenido.
- Si es valido, crea un workflow nuevo con ese grafo.
- Si hay errores, devuelve lista detallada de validaciones fallidas.

### 3) Compatibilidad por version

- El JSON de plantilla debe incluir campo de version, por ejemplo:

```json
{
  "template_version": "1.0",
  "workflow": {
    "name": "Mi Plantilla",
    "nodes": [],
    "edges": []
  }
}
```

- Si la version no es soportada, responder error controlado con mensaje accionable.

### 4) Seguridad y sanitizacion

- Ignorar campos no permitidos fuera del esquema de plantilla.
- Limitar tamano maximo de archivo importado.
- Sanitizar strings basicos (`name`, `label`) para evitar payloads anmalos.

## Diseno Backend

### 1) Nuevos endpoints

Agregar endpoints en blueprint de workflows:

- `GET /api/workflows/<workflow_id>/template/export`
  - Respuesta: JSON de plantilla.
- `POST /api/workflows/template/import`
  - Entrada: JSON de plantilla (multipart o body JSON).
  - Salida: workflow creado (`workflow_id`, `name`).

### 2) Helpers de plantilla

Crear modulo dedicado, sugerido:

- `app/api/template_io.py` o `app/services/template_service.py`

Responsabilidades:

- `build_template_payload(workflow)`
- `validate_template_payload(payload)`
- `sanitize_template_payload(payload)`
- `create_workflow_from_template(payload)`

### 3) Validaciones minimas

- `template_version` requerido.
- `workflow.nodes` lista valida.
- `workflow.edges` lista valida.
- cada nodo requiere `id`, `type`, `config` (dict).
- cada edge requiere `source_node_id`, `target_node_id`.
- reutilizar `validate_graph()` para validacion semantica final.

## Diseno Frontend

### 1) Accion Export

En toolbar/menu del editor:

- boton `Export Template`.
- llama endpoint export.
- descarga archivo como `workflow-template-<name>.json`.

### 2) Accion Import

En pantalla principal/editor:

- boton `Import Template`.
- selector de archivo `.json`.
- preview basico (nombre, numero de nodos/edges) opcional.
- confirmacion para crear nuevo workflow.

### 3) UX de errores

- Mostrar toast/dialog con errores de validacion retornados por backend.
- Si importacion exitosa, redirigir al workflow nuevo.

## Contrato JSON Propuesto (v1)

```json
{
  "template_version": "1.0",
  "exported_at": "2026-06-23T12:00:00Z",
  "source": {
    "workflow_id": "uuid-opcional",
    "app_version": "opcional"
  },
  "workflow": {
    "name": "Plantilla de Onboarding",
    "nodes": [
      {
        "id": "n1",
        "type": "set_variables",
        "label": "Set Variables",
        "config": {
          "variables": []
        }
      }
    ],
    "edges": []
  }
}
```

## Criterios de Aceptacion

1. Existe opcion para exportar un workflow a archivo JSON de plantilla.
2. Existe opcion para importar plantilla JSON y crear workflow nuevo.
3. La importacion valida esquema y reglas del grafo antes de guardar.
4. Los errores de importacion son claros y accionables.
5. El formato de plantilla incluye `template_version`.
6. El workflow importado abre correctamente en editor con nodos y conexiones.

## Riesgos y Mitigaciones

- Riesgo: plantillas de versiones antiguas/incompatibles.
  - Mitigacion: `template_version` y mensajes de incompatibilidad.
- Riesgo: payloads grandes o maliciosos.
  - Mitigacion: limite de tamano + validacion estricta + sanitizacion.
- Riesgo: nodos removidos/renombrados entre versiones.
  - Mitigacion: error explicito por `Unknown node type` y guia de correccion.

## Plan por Fases

### Fase A - Backend export

1. Crear helper para serializar workflow a formato plantilla v1.
2. Exponer endpoint `export`.

### Fase B - Backend import

1. Crear validacion de schema + sanitizacion.
2. Integrar `validate_graph()` y creacion de workflow.
3. Exponer endpoint `import`.

### Fase C - Frontend

1. Agregar botones `Export Template` e `Import Template`.
2. Implementar descarga de archivo y carga desde file input.
3. Manejo de errores y redireccion post-import.

### Fase D - Verificacion

1. Exportar workflow real y revisar JSON generado.
2. Importar el mismo JSON y validar que replica nodos/edges.
3. Probar casos invalidos (sin version, schema roto, nodo desconocido).

## Archivos Objetivo (Sugeridos)

- `app/api/workflows.py` (o blueprint equivalente para endpoints)
- `app/services/template_service.py` (nuevo)
- `frontend/src/pages/EditorPage.jsx` (acciones UI)
- `frontend/src/components/*` (dialog/file input de import)
- `README.md` (seccion de plantillas)
