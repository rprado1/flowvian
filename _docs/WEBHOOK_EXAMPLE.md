# Ejemplo rapido: Webhook + Set Variables

Este ejemplo crea un workflow que expone `POST /orders` y responde JSON al caller.

## Flujo

- Nodo 1: `Webhook`
- Nodo 2: `Set Variables`
- Edge: `Webhook.output_1 -> Set Variables.input_1`

## Configuracion recomendada

### 1) Webhook

```json
{
  "method": "POST",
  "host": "0.0.0.0",
  "port": 8088,
  "path": "/orders",
  "input_params": [
    { "name": "order_id", "source": "query", "type": "number", "required": true },
    { "name": "customer", "source": "body", "type": "string", "required": true }
  ],
  "response_body_var": "webhook_response_body",
  "response_status_var": "webhook_status_code",
  "response_headers_var": "webhook_headers"
}
```

### 2) Set Variables

Agrega estas variables (en el mismo orden):

1. `webhook_response_body` (type: `object`, value mode: `literal`)

```json
{
  "ok": true,
  "message": "Order received"
}
```

2. `webhook_status_code` (type: `number`, value mode: `literal`) = `201`
3. `webhook_headers` (type: `object`, value mode: `literal`)

```json
{
  "X-Workflow": "workflow-exe",
  "X-Webhook": "orders"
}
```

4. `received_order_id` (type: `number`, value mode: `template`) = `${order_id}`
5. `received_customer` (type: `string`, value mode: `template`) = `${customer}`

Tip: activa `Include Other Input Fields` en Set Variables.

## Probar con curl

Compila el workflow y ejecuta el `.exe` generado. Luego prueba:

```bash
curl -i -X POST "http://127.0.0.1:8088/orders?order_id=123" \
  -H "Content-Type: application/json" \
  -d "{\"customer\":\"Ana\"}"
```

Respuesta esperada (ejemplo):

```http
HTTP/1.0 201 Created
Content-Type: application/json; charset=utf-8
X-Workflow: workflow-exe
X-Webhook: orders

{"ok": true, "message": "Order received"}
```

## Variables disponibles en el flujo

El webhook inyecta en el item de entrada:

- `webhook_request`
- `webhook_method`
- `webhook_path`
- `webhook_query`
- `webhook_headers`
- `webhook_body`
- `webhook_params`
