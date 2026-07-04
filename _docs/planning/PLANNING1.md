# Planificacion: trigger unico y ejecucion condicionada por trigger

## Objetivo

Implementar una regla global para que cada workflow tenga **exactamente un nodo trigger de inicio** y que la ejecucion del flujo solo ocurra cuando exista ese trigger valido.

Triggers actuales contemplados:

- `webhook`
- `scheduler`

Si un workflow no tiene trigger, o tiene una configuracion invalida de trigger, debe omitirse del conjunto de resultados de ejecucion (no debe correr parcialmente).

---

## Alcance funcional

- Restringir el grafo para permitir solo 1 trigger por workflow.
- Asegurar que la ejecucion completa del flujo dependa de un trigger inicial.
- Omitir workflows sin trigger en listados/resultados de ejecucion.
- Agregar en frontend una seccion visual `Triggers` en menus de seleccion de nodos.

Fuera de alcance inicial:

- Nuevos tipos de trigger adicionales a `webhook` y `scheduler`.
- Ejecucion manual "forzada" de workflows sin trigger (se puede evaluar en otra fase con flag explicito).

---

## Reglas de negocio propuestas

1. Un workflow puede tener **0 o 1 trigger** durante edicion, pero para ejecutar debe tener **1 trigger obligatorio**.
2. Si existen 2 o mas triggers en el grafo, la validacion debe fallar con error claro.
3. Si no existe trigger, el workflow:
   - no debe iniciar ejecucion,
   - no debe aparecer como ejecutable en resultados/listas de corrida.
4. El trigger debe actuar como nodo de entrada principal del flujo.
5. Cualquier nodo no conectado (o subgrafo) sin dependencia del trigger inicial debe ignorarse en runtime (opcional v1, recomendado validar en fase 2).

---

## Cambios backend

## 1) Validacion de grafo

Componentes a tocar (referencial):

- `app/codegen/generator.py` (validacion de estructura y orden de ejecucion)
- `app/api/builder.py` (validacion previa a preview/run/build)

Acciones:

- Identificar nodos tipo trigger (`webhook`, `scheduler`).
- Contar triggers por workflow.
- Reglas de validacion:
  - `count == 0`: invalido para ejecutar.
  - `count > 1`: invalido.
  - `count == 1`: valido (si el resto del grafo cumple reglas actuales).
- Mensajes de error accionables (ejemplo: "El workflow debe tener exactamente un trigger: webhook o scheduler").

## 2) Filtro de workflows ejecutables

Acciones:

- En endpoints/servicios de ejecucion, omitir workflows sin trigger valido.
- En respuestas agregadas de resultados, excluir explicitamente workflows omitidos o marcarlos como `skipped` con motivo (`missing_trigger`), segun contrato API actual.

Decision recomendada v1:

- Mantener trazabilidad devolviendo estado `skipped` + motivo, en vez de omision silenciosa.

## 3) Codegen/runner

Acciones:

- Garantizar que el punto de entrada generado parte del trigger unico.
- Evitar generar ruta de ejecucion iniciando desde nodos no trigger.

---

## Cambios frontend

## 1) Menus de seleccion: seccion `Triggers`

Componentes a tocar (referencial):

- Registro de nodos y metadata en `frontend/src/nodes/index.js`
- UI del menu/palette de creacion de nodos (componente donde se agrupan categorias)

Acciones:

- Crear categoria visual `Triggers`.
- Mover/mostrar `webhook` y `scheduler` dentro de esa categoria.
- Mantener categorias existentes para nodos no trigger.

## 2) Restriccion en UI (solo un trigger)

Acciones:

- Si ya existe trigger en el canvas:
  - deshabilitar agregar otro trigger desde menu, o
  - permitir click pero mostrar error y no insertar nodo.
- Mensaje recomendado: "Solo se permite un trigger por workflow".

## 3) Validaciones UX previas a ejecutar

Acciones:

- Antes de `preview/run/build`, mostrar error bloqueante si no hay trigger.
- Si hay mas de un trigger (por datos legacy), mostrar error bloqueante y guiar a corregir.

---

## Compatibilidad y migracion

- Workflows existentes sin trigger:
  - no se rompen al abrir/editar,
  - pero quedan no ejecutables hasta agregar trigger.
- Workflows legacy con multiples triggers:
  - abrir con advertencia,
  - bloquear ejecucion hasta dejar solo uno.
- No alterar automaticamente grafos existentes sin confirmacion del usuario.

---

## Plan por fases

## Fase 1 - Validacion y reglas backend

- Implementar conteo y validacion de trigger unico.
- Bloquear ejecucion sin trigger o con multiples triggers.
- Definir contrato de salida para workflows omitidos (`skipped` recomendado).

## Fase 2 - Ajustes frontend

- Agregar seccion `Triggers` en menu de seleccion.
- Restringir insercion de segundo trigger.
- Agregar mensajes de validacion previos a run/preview/build.

## Fase 3 - Compatibilidad y DX

- Manejar workflows legacy con advertencias claras.
- Documentar mensajes de error y pasos de correccion.
- Ajustar textos UI para consistencia (trigger unico, trigger requerido).

## Fase 4 - Verificacion final

- Smoke tests de creacion/edicion/ejecucion.
- Confirmar que resultados omiten o marcan `skipped` workflows sin trigger.
- Validar UX del menu con categoria `Triggers`.

---

## Criterios de aceptacion

1. No se puede ejecutar un workflow sin trigger.
2. No se puede ejecutar un workflow con mas de un trigger.
3. El frontend muestra una categoria `Triggers` con `webhook` y `scheduler`.
4. El frontend evita agregar un segundo trigger en el canvas.
5. En resultados de ejecucion, workflows sin trigger no corren y quedan omitidos o `skipped` segun contrato definido.
6. Los errores son claros y accionables para usuario final.

---

## Casos de prueba sugeridos

- Caso A: workflow sin trigger + run -> bloqueado con error de trigger requerido.
- Caso B: workflow con `webhook` unico + run -> ejecuta OK.
- Caso C: workflow con `scheduler` unico + run -> ejecuta OK.
- Caso D: workflow con `webhook` + `scheduler` + run -> bloqueado por trigger multiple.
- Caso E: en UI, con trigger existente intentar agregar otro -> no permitido.
- Caso F: listado de ejecucion con workflows mixtos -> solo ejecutables incluidos (o resto `skipped`).

---

## Riesgos y mitigaciones

- Riesgo: workflows legacy dejan de ejecutar sin aviso.
  - Mitigar con advertencias en UI + motivos `skipped` en API.
- Riesgo: inconsistencia entre validacion frontend y backend.
  - Mitigar manteniendo backend como fuente de verdad y frontend como pre-validacion UX.
- Riesgo: cambios en resultados rompen consumidores API.
  - Mitigar con contrato explicito y versionado si aplica.
