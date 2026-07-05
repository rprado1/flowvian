# Plan de publicacion en PyPI (Workflow Builder)

## Objetivo

Publicar Workflow Builder como paquete de PyPI para que un usuario pueda instalar y ejecutar la aplicacion con comandos simples:

```bash
pip install workflow-builder
wbui start
```

Resultado esperado: `wbui start` inicia backend + frontend y deja la UI disponible en `http://localhost:5007` (o en el puerto definido con `-p`).

---

## Alcance del plan

- Empaquetado Python moderno con `pyproject.toml`.
- Publicacion del paquete en PyPI (con validacion previa en TestPyPI).
- Exposicion del CLI `wbui` mediante `project.scripts`.
- Soporte de ejecucion `wbui start` con puerto opcional `-p`.
- Inclusion de assets compilados del frontend dentro del paquete.
- Flujo de release manual y repetible.

Fuera de alcance inicial:

- Distribucion como binario nativo para usuarios sin Python.
- Instaladores nativos del sistema operativo.

---

## Arquitectura de distribucion

### Opcion recomendada (v1): paquete Python unico en PyPI

1. Compilar frontend React con `npm run build`.
2. Asegurar que el build final quede en `app/static/dist/`.
3. Empaquetar codigo Python + assets frontend en wheel/sdist.
4. Publicar en PyPI con entrypoint CLI.
5. Ejecutar localmente con `wbui start`.

Ventajas:

- Flujo estandar del ecosistema Python.
- Menor complejidad operativa para v1.
- Versionado y dependencias centralizados en PyPI.

Limitacion conocida:

- El usuario final necesita Python compatible instalado.

---

## Cambios tecnicos requeridos

## 1) Definir metadatos y build system en `pyproject.toml`

Acciones:

- Crear/actualizar `pyproject.toml` con `setuptools.build_meta`.
- Definir `project.name` (recomendado: `workflow-builder`).
- Definir `version`, `description`, `readme`, `requires-python`.
- Declarar dependencias runtime del backend.
- Exponer script de consola:

```toml
[project.scripts]
wbui = "run:cli"
```

## 2) Estandarizar CLI en `run.py`

Estado actual:

- `run.py` solo ejecuta desde `if __name__ == "__main__":`.
- No hay parser CLI ni subcomandos.

Acciones:

- Agregar `main(port=None)` para iniciar Flask.
- Agregar `cli()` con `argparse`.
- Definir subcomando `start`.
- Soportar puerto opcional solo como `-p` (sin `--port` ni `--p`).

Uso esperado:

```bash
wbui start
wbui start -p 5007
```

Regla CLI acordada:

- Parametro de puerto: solo `-p`.
- No habilitar alias largos.

## 2.1) Persistencia portable por usuario

Acciones:

- Mover almacenamiento por defecto fuera del repo hacia carpetas por usuario.
- Definir rutas por OS:
  - Windows: `%APPDATA%/WorkflowBuilder`
  - Linux: `~/.config/workflow-builder`
  - macOS: `~/Library/Application Support/WorkflowBuilder`
- Mantener overrides por variables de entorno:
  - `WBUI_DATA_DIR`
  - `WBUI_OUTPUT_DIR`
- No realizar migracion automatica desde rutas del repo para mantener instalacion limpia en PyPI.

Resultado esperado:

- `wbui start` usa una ubicacion persistente y consistente, independiente del directorio desde donde se ejecuta.

## 3) Build frontend para distribucion

Acciones:

- Ejecutar `npm install` y `npm run build` en `frontend/` antes de empaquetar.
- Validar que Flask sirva correctamente el build desde `app/static/dist/`.

## 4) Incluir assets frontend en wheel/sdist

Acciones:

- Agregar `MANIFEST.in` con inclusion recursiva de `app/static/dist`.
- Configurar `tool.setuptools.package-data` para incluir estaticos en wheel.

Validacion:

- Tras instalar wheel, los assets existen en `site-packages`.
- La UI abre sin depender del codigo fuente de `frontend/`.

## 5) Flujo de build y publicacion

Acciones:

- Instalar herramientas de release: `build` y `twine`.
- Generar artefactos con `python -m build`.
- Validar metadata con `twine check dist/*`.
- Publicar en TestPyPI.
- Publicar en PyPI.

## 6) Documentacion de instalacion

Acciones:

- Actualizar `README.md` con instalacion desde PyPI.
- Documentar ejecucion con `wbui start` y `wbui start -p 5007`.
- Agregar troubleshooting basico.

---

## Plan por fases

## Fase 0 - Pre-flight

- Confirmar disponibilidad del nombre `workflow-builder` en PyPI.
- Definir `requires-python` segun soporte real.
- Definir politica de versionado.
- Crear API token para TestPyPI/PyPI.

## Fase 1 - Preparar empaquetado

- Crear/ajustar `pyproject.toml`.
- Implementar `run:cli` con subcomando `start` y opcion `-p`.
- Definir inclusion de estaticos (`MANIFEST.in` + package-data).
- Implementar rutas de datos/salida por usuario + migracion inicial.

## Fase 2 - Validacion local

- Build frontend.
- Instalar localmente con `pip install -e .`.
- Ejecutar `wbui start` y `wbui start -p 5007`.
- Verificar que los datos se creen/lean desde la carpeta de usuario.
- Probar `python -m build` y revisar wheel/sdist.

## Fase 3 - Publicacion controlada

- Subir a TestPyPI.
- Probar instalacion desde TestPyPI en entorno limpio.
- Ajustar problemas de metadata/dependencias/archivos.

## Fase 4 - Publicacion oficial

- Publicar version estable en PyPI.
- Verificar instalacion real con `pip install workflow-builder`.
- Publicar notas de release.

---

## Criterios de aceptacion

Se considera completado cuando:

1. `pip install workflow-builder` finaliza sin errores en entorno limpio con Python soportado.
2. `wbui start` inicia la app local y expone la UI en `http://localhost:5007`.
3. `wbui start -p 5007` funciona y sobrescribe el puerto por defecto.
4. Frontend compilado carga correctamente desde el paquete instalado.
5. El proceso de release queda documentado y es repetible.

---

## Riesgos y mitigaciones

- Archivos estaticos faltantes en wheel:
  - Mitigar con `MANIFEST.in`, `package-data` y validacion post-install.
- Diferencias entre entorno dev e instalado:
  - Mitigar con pruebas en venv limpio y rutas relativas basadas en paquete.
- Conflictos de nombre en PyPI:
  - Definir nombre alternativo antes del release.
- Puerto ocupado:
  - Mostrar mensaje claro y documentar uso de `-p`.

---

## Entregables

- `pyproject.toml` con metadata y `project.scripts`.
- `MANIFEST.in` y configuracion de package-data.
- `run.py` con `cli()` + subcomando `start` + opcion `-p`.
- `README.md` actualizado para instalacion y uso desde PyPI.
- Guia de release manual (TestPyPI -> PyPI).

---

## Comandos de validacion recomendados

```bash
# 1) Build frontend
cd frontend
npm install
npm run build

# 2) Volver a raiz del repositorio y validar import
cd ..
python -c "from app.main import app; print('OK')"

# 3) Instalar en modo editable y ejecutar CLI
pip install -e .
wbui start
wbui start -p 5007

# 4) Generar artefactos
python -m build
twine check dist/*

# 5) Publicar en TestPyPI (primero)
twine upload --repository testpypi dist/*

# 6) Publicar en PyPI
twine upload dist/*
```

Validacion de experiencia final de usuario (entorno limpio):

```bash
pip install workflow-builder
wbui start
```

---

## Mejoras recomendadas (v1.1+)

- `wbui doctor` para diagnostico rapido (puerto, permisos, rutas).
- Apertura automatica del navegador al iniciar.
- Carpeta de configuracion por sistema operativo para datos de usuario.
- Publicacion adicional como ejecutable standalone para usuarios sin Python.
