# PLANNING3 - Nodo Sort

## 1) Objetivo

Implementar un nodo `sort` que permita ordenar los items del flujo por un campo, con orden ascendente o descendente.

El nodo debe:

- recibir una lista de items (`_items`),
- ordenar por un campo configurable,
- soportar `asc` y `desc`,
- devolver la lista ordenada por su unica salida.

---

## 2) Alcance funcional

### Incluido

- Nuevo nodo backend `sort`.
- Configuracion de campo de orden y direccion (`asc`/`desc`).
- Soporte de path simple/compuesto para campo (ej: `amount`, `user.name`, `items[0].price`).
- Integracion con validate/preview/run/build.
- Nodo frontend con props form simple.

### No incluido (por ahora)

- Multi-sort (ordenar por multiples campos).
- Opciones de locale/collation avanzada para texto.
- Politicas complejas de nulls first/last configurables.

---

## 3) Semantica de ejecucion

Entrada:

- `_items` (lista de objetos).

Ejecucion:

1. Leer `field_path` configurado.
2. Obtener valor de cada item segun path.
3. Ordenar lista completa por ese valor.
4. Aplicar direccion (`asc` o `desc`).

Salida:

- `_items` ordenada.
- `_branch_outputs = {'output_1': _items}`.

Comportamiento recomendado para valores faltantes:

- Si un item no tiene el campo/path, fallar con error explicito (mas seguro para automatizaciones).

---

## 4) Contrato de configuracion propuesto

Config base:

```json
{
  "field_path": "id",
  "order": "asc"
}
```

Reglas:

- `field_path`: requerido, string no vacio.
- `order`: requerido, solo `asc` o `desc`.

Compatibilidad sugerida:

- aceptar alias `direction` si aparece en versiones futuras, pero persistir `order` como canonico.

---

## 5) Cambios backend

## 5.1 Nuevo nodo

Crear `app/nodes/sort.py` con `SortNode(BaseNode)`.

### validate()

- validar `field_path` no vacio.
- validar `order` en (`asc`, `desc`).

### to_code()

- usar helper runtime `_resolve_item_path(_item, _path)` ya presente en scripts generados.
- construir clave segura para sort, evitando errores de comparacion entre tipos mixtos.
- ejemplo de estrategia de key:
  - prioridad por tipo (`None`, bool, number, string, list, dict, otros),
  - valor normalizado para comparar.
- aplicar `reverse=True` cuando `order == 'desc'`.
- poblar `_node_debug` con `field_path`, `order`, `items_in`, `items_out`.

## 5.2 Registro

Actualizar `app/codegen/generator.py`:

- importar `SortNode`.
- registrar en `NODE_REGISTRY`.

---

## 6) Cambios frontend

## 6.1 Nodo visual

Crear `frontend/src/nodes/SortNode.jsx`:

- 1 entrada, 1 salida.
- resumen visual: `field_path` + `order`.

## 6.2 PropsForm

Campos:

1. `Field path` (texto): `amount`, `user.name`, `rows[0].total`.
2. `Order` (select): `Ascending (asc)` / `Descending (desc)`.

## 6.3 Registro en catalogo

Actualizar `frontend/src/nodes/index.js`:

- `nodeTypes.sort = SortNode`.
- `NODE_META.sort` con `defaultConfig` y `PropsForm`.

## 6.4 Selector de nodos

- Agregar `sort` a categoria `Data`.

---

## 7) Pruebas sugeridas

## Backend

1. Orden asc por numero.
2. Orden desc por numero.
3. Orden por string.
4. Orden por path anidado (`user.name`).
5. Item sin campo/path -> error esperado.
6. Lista vacia -> salida vacia sin error.

## Integracion

7. Flujo `set_variables -> sort -> ...` mantiene orden correcto.
8. `preview`, `run` y `build` sin regresiones.

## Frontend

9. Config persiste tras guardar/cargar workflow.
10. Node selector muestra `Sort` y permite agregarlo al canvas.

---

## 8) Riesgos y mitigaciones

### Riesgos

- Datos con tipos mixtos que pueden romper comparacion nativa en Python.
- Ambiguedad sobre como ordenar nulls y valores faltantes.

### Mitigaciones

- Definir key de sort tipada y deterministica.
- Fallar temprano cuando falte `field_path` en algun item.
- Documentar comportamiento en README/checklist cuando se implemente.

---

## 9) Resultado esperado

Contar con un nodo `sort` estable y predecible para ordenar la lista del flujo en `asc` o `desc` por un campo configurable, facilitando procesos de priorizacion, ranking y preparacion de datos antes de pasos posteriores.
