# Plan de publicacion en npm (`wbui`)

## Objetivo

Publicar el proyecto como paquete global de npm para que un usuario pueda:

```bash
npm install -g wbui
wbui start
```

Y que `wbui start` levante la aplicacion en `http://localhost:5007`.

Condicion obligatoria: el usuario final **no** debe instalar Python ni dependencias adicionales fuera de Node.js/npm.

Contexto actual: el proyecto ya esta publicado en GitHub y existe tag/release base:

- `v1.0.0-alpha.8`
- `https://github.com/rprado1/workflow-exe/releases/tag/v1.0.0-alpha.8`

---

## Alcance del plan

- Empaquetado del proyecto para distribucion por npm.
- Comando CLI global `wbui`.
- Subcomando `start` con puerto fijo `5007` (y opcionalmente configurable a futuro).
- Flujo de build reproducible para generar artefactos.
- Publicacion y versionado en npm.
- Instalacion zero-deps para usuario final (sin Python, sin `pip`, sin venv).
- Soporte multiplataforma para instalacion y ejecucion: Windows y Linux.
- Proceso de release manual (sin GitHub Actions).

Fuera de alcance inicial:

- Instalador nativo (MSI/EXE installer) fuera de npm.

---

## Arquitectura propuesta de distribucion

### Opcion recomendada (v1): un solo paquete npm + binarios por plataforma

1. Construir binarios nativos de la app backend para cada plataforma objetivo, con frontend ya compilado.
2. Publicar un unico paquete npm `wbui` con CLI Node.js (`bin/wbui.js`).
3. En instalacion (o prepack/release), seleccionar y descargar el binario segun `platform + arch` desde GitHub Releases.
4. `wbui start` ejecuta el binario local y fuerza `PORT=5007`.

Ventajas:

- Usuario final no necesita Python instalado.
- Usuario final no ejecuta `pip install` ni configura entorno virtual.
- Experiencia simple con `npm install -g` en Windows y Linux.
- Menor variabilidad de entorno.

Riesgo:

- Complejidad operativa por builds manuales por plataforma.

### Opcion alternativa: npm wrapper + Python local

`wbui start` llama `python run.py`.

No recomendada para v1 porque depende de Python/venv instalado y configurado en el equipo del usuario.

---

## Cambios tecnicos requeridos

## 1) Ajustar puerto de arranque a 5007

Archivos objetivo:

- `run.py`
- (opcional) `app/main.py` bloque `__main__`

Acciones:

- Cambiar puerto por defecto de `5000` a `5007` en `run.py`.
- Recomendado: leer variable de entorno `PORT`, con fallback `5007`.
- Mantener `debug=True` solo para entorno desarrollo; para release, evaluar modo no-debug.

Resultado esperado:

- `wbui start` inicia en `5007` consistentemente.

## 2) Crear CLI de npm (`wbui`)

Estructura sugerida:

```text
package.json
bin/
  wbui.js
scripts/
  build-npm.js (opcional)
```

`package.json` minimo:

- `name: "wbui"`
- `version: "0.1.0"`
- `bin: { "wbui": "bin/wbui.js" }`
- `files` incluyendo solo runtime necesario.
- `os` restringido a Windows si el binario lo requiere.

Comportamiento CLI v1:

- `wbui start`: ejecuta app en puerto `5007`.
- `wbui --help`: muestra comandos.
- `wbui --version`: version del paquete.

## 3) Build frontend para distribucion

Acciones:

- Ejecutar `frontend/npm run build` en pipeline de release.
- Verificar que `app/static/dist/` se incluya dentro del artefacto final.
- Confirmar que rutas SPA siguen funcionando en ejecutable.

## 4) Generar binario distribuible

Acciones:

- Crear script de build de release (ej: `scripts/build_release.bat` o Python).
- Ejecutar build para cada plataforma objetivo (Windows/Linux) y arquitectura soportada.
- Publicar assets por plataforma en GitHub Release (nombres estables por `platform-arch`).
- Configurar resolucion automatica de asset en instalacion npm.

Verificaciones:

- Binario inicia Flask correctamente.
- Sirve frontend compilado.
- No depende de rutas absolutas del repo.

## 5) Empaquetado npm

Acciones:

- Crear `package.json` en raiz del repo o en carpeta `npm/` dedicada.
- Definir `prepack` para:
  1. Build frontend.
  2. Build/publicacion de binarios por plataforma.
  3. Resolucion de runtime segun OS/arquitectura.
- Asegurar que el paquete publicado contenga todo lo necesario para ejecutar `wbui start` sin descargar dependencias externas en postinstall.
- Probar localmente con `npm pack`.

Validacion local:

```bash
npm pack
npm install -g ./wbui-0.1.0.tgz
wbui start
```

## 6) Publicacion en npm

Checklist:

- Verificar disponibilidad del nombre `wbui`.
- Iniciar sesion: `npm login`.
- Publicar: `npm publish --access public`.
- Probar desde entorno limpio:

```bash
npm install -g wbui
wbui start
```

---

## Plan por fases

## Fase 0 - Pre-flight

- Confirmar que el nombre `wbui` esta disponible en npm.
- Definir politica de versionado (SemVer).
- Definir matriz de soporte v1: Windows y Linux (x64 como minimo).
- Confirmar proceso manual de release (sin GitHub Actions).
- Tomar como referencia el release existente `v1.0.0-alpha.8` para trazabilidad del primer publish en npm.

## Fase 1 - Preparar runtime

- Ajustar puerto por defecto a `5007`.
- Asegurar que frontend build queda embebido.
- Verificar ejecucion local sin dependencias del entorno dev.
- Definir convencion de nombres de assets por plataforma/arquitectura.

## Fase 2 - CLI npm

- Crear `package.json` y `bin/wbui.js`.
- Implementar comando `start`.
- Agregar `help/version`.

## Fase 3 - Proceso de release manual

- Ejecutar manualmente build frontend + binarios Windows/Linux + empaquetado npm.
- Subir manualmente assets al GitHub Release correspondiente.
- Generar `.tgz` con `npm pack`.
- Ejecutar smoke tests de instalacion global.

## Fase 4 - Publicacion

- Publicar `0.1.0`.
- Validar instalacion real desde npm registry.
- Documentar troubleshooting inicial.

---

## Criterios de aceptacion

Se considera completado cuando:

1. `npm install -g wbui` finaliza sin errores en Windows y Linux limpios.
2. `wbui start` levanta el servicio en `http://localhost:5007` en ambas plataformas.
3. La UI carga correctamente y responde API basica.
4. `wbui --help` y `wbui --version` funcionan.
5. El usuario final no necesita instalar Python, `pip`, ni otras librerias del sistema para ejecutar `wbui`.
6. El proceso de release esta documentado y repetible.

---

## Riesgos y mitigaciones

- Tamano grande del paquete npm por binario:
  - Mitigar excluyendo archivos no esenciales con `files`/`.npmignore`.
- Incompatibilidad por arquitectura (x64 vs arm64):
  - Publicar matriz de soporte y resolver asset por `platform-arch`.
- Puerto ocupado (5007):
  - v1: mensaje claro de error.
  - v1.1: fallback automatico o flag `--port`.
- Falsos positivos de antivirus sobre binarios:
  - Firmado de codigo y documentar hashes/checksums en roadmap.
- Diferencias de libc en Linux:
  - Generar build en entorno compatible (baseline glibc) y validar en distro objetivo.

---

## Entregables

- `package.json` para npm global package.
- `bin/wbui.js` con comando `start`.
- Script de release automatizado (build frontend + pyinstaller + pack).
- README actualizado con instalacion por npm.
- Checklist de publicacion y rollback basico.

---

## Comandos de validacion recomendados

```bash
# Comandos para maintainers (release), no para usuario final

# 1) Build frontend
cd frontend && npm install && npm run build

# 2) Build binario (segun script definido)
python -m PyInstaller <spec_o_parametros>

# 3) Empaquetar npm
npm pack

# 4) Instalar paquete local generado
npm install -g ./wbui-<version>.tgz

# 5) Ejecutar CLI
wbui start
```

Validacion de experiencia final de usuario (equipo limpio):

```bash
npm install -g wbui
wbui start
```

Si estos dos comandos funcionan en equipos limpios de Windows y Linux sin Python instalado, se cumple el requisito principal de instalacion.

---

## Roadmap posterior (v1.1+)

- `wbui start --port <n>` para puerto configurable.
- `wbui doctor` para diagnostico rapido (puerto, permisos, rutas).
- Publicacion de binarios por plataforma con descarga dinamica.
- Telemetria opcional y anonima (si aplica).
