# PLANNING7 - UX del menu de seleccion de nodos

## 1) Objetivo

Revisar la experiencia actual del menu de seleccion de nodos y proponer mejoras de UX que permitan escalar el catalogo sin degradar la velocidad de seleccion ni la claridad de uso.

Contexto del problema:

- La cantidad de nodos crecio.
- El area actual de seleccion se esta quedando pequena.
- El usuario tarda mas en encontrar nodos y aumenta la friccion operativa.

---

## 2) Alcance

### Incluido

- Analisis UX del selector actual.
- Identificacion de problemas de usabilidad, navegacion y descubrimiento.
- Evaluacion de patrones similares (n8n, Node-RED, Make, etc.).
- Definicion y comparacion de alternativas de rediseno.
- Propuesta visual conceptual (wireframes/mockups de baja fidelidad).
- Recomendacion de solucion objetivo.
- Plan de implementacion por fases.

### No incluido (por ahora)

- Implementacion de codigo frontend/backend.
- Migraciones de datos o cambios de persistencia.
- QA funcional final del rediseno implementado.

---

## 3) Actividades de analisis

1. Revisar el comportamiento actual del selector y documentar puntos de friccion.
2. Analizar distribucion actual de nodos, categorias, jerarquia visual y accesibilidad.
3. Mapear tareas frecuentes del usuario (agregar nodo comun, encontrar nodo especifico, reusar nodo reciente).
4. Evaluar patrones de herramientas similares para catalogos grandes.
5. Definir alternativas de mejora y compararlas.
6. Estimar impacto tecnico y complejidad de implementacion por alternativa.
7. Producir wireframes conceptuales de las opciones mas viables.
8. Recomendar alternativa final con justificacion.

---

## 4) Alternativas a evaluar

Cada alternativa debe evaluarse con: usabilidad, escalabilidad, costo tecnico, mantenibilidad, impacto en performance y riesgo de adopcion.

1. Busqueda rapida por nombre/palabra clave (con ranking por relevancia).
2. Agrupacion por categorias (Input, Transform, Flow, HTTP, Utility, etc.).
3. Menus jerarquicos o grupos expandibles/colapsables.
4. Panel lateral dedicado con mayor ancho y scroll optimizado.
5. Seccion de favoritos y nodos recientes.
6. Filtros dinamicos (categoria, tipo de salida, popularidad).
7. Selector ampliado en modal o vista de pantalla completa.
8. Combinacion hibrida (busqueda + categorias + recientes), como candidato principal.

---

## 5) Criterios de decision

Matriz de evaluacion sugerida (1 a 5, con ponderacion):

- Tiempo para encontrar un nodo (25%).
- Facilidad de aprendizaje para usuarios nuevos (20%).
- Eficiencia para usuarios recurrentes (20%).
- Complejidad de implementacion (15%).
- Mantenibilidad futura (10%).
- Riesgo de regresiones UX/tecnicas (10%).

La alternativa recomendada debe justificar el puntaje final y trade-offs.

---

## 6) Entregables

1. Documento de analisis UX del selector actual.
2. Comparativa de alternativas con ventajas, desventajas y costo tecnico.
3. Wireframes/mockups conceptuales de opciones viables.
4. Recomendacion de solucion optima.
5. Plan de implementacion por fases (MVP + mejoras incrementales).

---

## 7) Plan de implementacion propuesto (posterior al analisis)

### Fase A - Quick wins (bajo costo)

- Busqueda por texto.
- Categorias colapsables.
- Ajustes de layout para aumentar area util del selector.

### Fase B - Mejora estructural

- Panel dedicado o modal ampliado.
- Favoritos/recientes.
- Filtros dinamicos.

### Fase C - Optimizacion

- Ranking inteligente de resultados (por uso/recencia).
- Atajos de teclado para abrir selector y focus en busqueda.
- Medicion de metricas UX (tiempo de seleccion, tasa de exito al primer intento).

---

## 8) Riesgos y mitigaciones

- Riesgo: sobrecargar la UI con muchas opciones.
  - Mitigacion: priorizar MVP simple (busqueda + categorias).
- Riesgo: cambios visuales que rompan flujo actual de usuarios.
  - Mitigacion: mantener patrones actuales y aplicar cambios graduales.
- Riesgo: degradacion de performance con catalogo grande.
  - Mitigacion: render virtualizado/listado paginado si aplica.

---

## 9) Resultado esperado

Contar con una propuesta de rediseno que permita escalar el numero de nodos disponibles sin degradar la experiencia de usuario, facilitando una seleccion rapida, intuitiva y eficiente.

Este resultado de planificacion se almacenara explicitamente en:

- `_docs/planning/PLANNING7.md`
