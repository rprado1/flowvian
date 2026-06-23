from __future__ import annotations

from app.nodes.base import BaseNode


class WebhookNode(BaseNode):
    NODE_TYPE = "webhook"

    _METHODS = ("GET", "POST", "BOTH")
    _PARAM_TYPES = ("string", "number", "boolean", "object", "array")
    _PARAM_SOURCES = ("query", "body", "header")

    @staticmethod
    def _normalize_path(raw_value) -> str:
        path = str(raw_value or "").strip() or "/webhook"
        if not path.startswith("/"):
            path = "/" + path
        return path

    @staticmethod
    def _normalize_host(raw_value) -> str:
        host = str(raw_value or "").strip()
        return host or "0.0.0.0"

    @staticmethod
    def _to_int(raw_value, default: int) -> int:
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _normalize_param(cls, raw_param: dict) -> dict:
        name = str(raw_param.get("name", "")).strip()
        param_type = str(raw_param.get("type", "string")).strip().lower() or "string"
        source = str(raw_param.get("source", "query")).strip().lower() or "query"
        required = bool(raw_param.get("required", False))
        return {
            "name": name,
            "type": param_type,
            "source": source,
            "required": required,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []

        method = str(self.config.get("method", "POST")).strip().upper() or "POST"
        if method not in self._METHODS:
            errors.append("webhook: method must be GET, POST or BOTH")

        host = self._normalize_host(self.config.get("host", "0.0.0.0"))
        if not host:
            errors.append("webhook: host cannot be empty")

        port = self._to_int(self.config.get("port", 8000), 8000)
        if port < 1 or port > 65535:
            errors.append("webhook: port must be between 1 and 65535")

        path = self._normalize_path(self.config.get("path", "/webhook"))
        if " " in path:
            errors.append("webhook: path cannot contain spaces")

        input_params = self.config.get("input_params", [])
        if not isinstance(input_params, list):
            errors.append("webhook: input_params must be a list")
            input_params = []

        seen_names: set[str] = set()
        for idx, raw_param in enumerate(input_params):
            if not isinstance(raw_param, dict):
                errors.append(f"webhook: input_params[{idx}] must be an object")
                continue
            param = self._normalize_param(raw_param)
            name = param["name"]
            if not name:
                errors.append(f"webhook: input_params[{idx}] requires name")
                continue
            if not name.isidentifier():
                errors.append(f"webhook: input_params[{idx}] name '{name}' is not a valid identifier")
            if name in seen_names:
                errors.append(f"webhook: duplicated input param name '{name}'")
            seen_names.add(name)

            if param["type"] not in self._PARAM_TYPES:
                errors.append(
                    f"webhook: input_params[{idx}] type must be one of: {', '.join(self._PARAM_TYPES)}"
                )

            if param["source"] not in self._PARAM_SOURCES:
                errors.append(
                    f"webhook: input_params[{idx}] source must be one of: {', '.join(self._PARAM_SOURCES)}"
                )

        response_body_var = str(self.config.get("response_body_var", "")).strip()
        if response_body_var and not response_body_var.isidentifier():
            errors.append(
                f"webhook: response_body_var '{response_body_var}' is not a valid identifier"
            )

        response_status_var = str(self.config.get("response_status_var", "")).strip()
        if response_status_var and not response_status_var.isidentifier():
            errors.append(
                f"webhook: response_status_var '{response_status_var}' is not a valid identifier"
            )

        response_headers_var = str(self.config.get("response_headers_var", "")).strip()
        if response_headers_var and not response_headers_var.isidentifier():
            errors.append(
                f"webhook: response_headers_var '{response_headers_var}' is not a valid identifier"
            )

        return errors

    def to_code(self, indent: int = 0) -> str:
        method = str(self.config.get("method", "POST")).strip().upper() or "POST"
        host = self._normalize_host(self.config.get("host", "0.0.0.0"))
        port = self._to_int(self.config.get("port", 8000), 8000)
        path = self._normalize_path(self.config.get("path", "/webhook"))

        input_params = self.config.get("input_params", [])
        normalized_params = []
        if isinstance(input_params, list):
            for raw_param in input_params:
                if not isinstance(raw_param, dict):
                    continue
                param = self._normalize_param(raw_param)
                if not param["name"]:
                    continue
                normalized_params.append(param)

        response_body_var = str(self.config.get("response_body_var", "")).strip()
        response_status_var = str(self.config.get("response_status_var", "")).strip()
        response_headers_var = str(self.config.get("response_headers_var", "")).strip()

        lines = [
            "# WEBHOOK",
            f"_webhook_method = {method!r}",
            f"_webhook_host = {host!r}",
            f"_webhook_port = {port!r}",
            f"_webhook_path = {path!r}",
            f"_webhook_input_params = {normalized_params!r}",
            f"_webhook_response_body_var = {response_body_var!r}",
            f"_webhook_response_status_var = {response_status_var!r}",
            f"_webhook_response_headers_var = {response_headers_var!r}",
            "_serve_webhook(",
            "    method=_webhook_method,",
            "    host=_webhook_host,",
            "    port=_webhook_port,",
            "    path=_webhook_path,",
            "    input_params=_webhook_input_params,",
            "    response_body_var=_webhook_response_body_var,",
            "    response_status_var=_webhook_response_status_var,",
            "    response_headers_var=_webhook_response_headers_var,",
            "    workflow_handler=_execute_webhook_workflow,",
            ")",
        ]

        return self._indent("\n".join(lines), indent)
