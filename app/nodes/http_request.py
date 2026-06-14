import json
from urllib.parse import urlparse

from app.nodes.base import BaseNode


class HttpRequestNode(BaseNode):
    NODE_TYPE = "http_request"

    def validate(self) -> list[str]:
        errors: list[str] = []

        method = str(self.config.get("method", "GET")).upper()
        if method not in ("GET", "POST"):
            errors.append("http_request: method must be GET or POST")

        url = str(self.config.get("url", "")).strip()
        if not url:
            errors.append("http_request: url cannot be empty")
        elif not (url.startswith("http://") or url.startswith("https://")):
            errors.append("http_request: url must start with http:// or https://")

        query_params = self.config.get("query_params", [])
        if not isinstance(query_params, list):
            errors.append("http_request: query_params must be a list")
        else:
            for idx, item in enumerate(query_params):
                if not isinstance(item, dict):
                    errors.append(f"http_request: query param item {idx} must be an object")
                    continue
                key = str(item.get("key", "")).strip()
                if not key:
                    errors.append(f"http_request: query param item {idx} has empty key")

        raw_timeout = self.config.get("timeout_seconds", 30)
        try:
            timeout = float(raw_timeout)
            if timeout < 1 or timeout > 120:
                errors.append("http_request: timeout_seconds must be between 1 and 120")
        except (TypeError, ValueError):
            errors.append("http_request: timeout_seconds must be a number")

        headers = self.config.get("headers", [])
        if isinstance(headers, dict):
            for key, value in headers.items():
                if not str(key).strip():
                    errors.append("http_request: header key cannot be empty")
                if value is None:
                    errors.append(f"http_request: header '{key}' has null value")
        elif isinstance(headers, list):
            for idx, item in enumerate(headers):
                if not isinstance(item, dict):
                    errors.append(f"http_request: header item {idx} must be an object")
                    continue
                key = str(item.get("key", "")).strip()
                if not key:
                    errors.append(f"http_request: header item {idx} has empty key")
                if item.get("value") is None:
                    errors.append(f"http_request: header item {idx} has null value")
        else:
            errors.append("http_request: headers must be a list or object")

        if method == "POST":
            body_raw_json = str(self.config.get("body_raw_json", "")).strip()
            if not body_raw_json:
                errors.append("http_request: body_raw_json is required for POST")
            else:
                try:
                    json.loads(body_raw_json)
                except Exception:
                    errors.append("http_request: body_raw_json must be valid JSON")
        else:
            parsed = urlparse(url)
            if parsed.query:
                errors.append("http_request: GET URL must not include query string; use query_params")

        return errors

    def to_code(self, indent: int = 0) -> str:
        method = str(self.config.get("method", "GET")).upper()
        url = str(self.config.get("url", "")).strip()
        timeout_seconds = float(self.config.get("timeout_seconds", 30) or 30)
        body_raw_json = str(self.config.get("body_raw_json", "")).strip()
        query_params_config = self.config.get("query_params", [])
        headers_config = self.config.get("headers", [])

        if isinstance(query_params_config, list):
            normalized_query_params = []
            for item in query_params_config:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key", "")).strip()
                if not key:
                    continue
                value = item.get("value", "")
                normalized_query_params.append({"key": key, "value": "" if value is None else str(value)})
        else:
            normalized_query_params = []

        # Normalize headers config to list[dict{key,value}] for deterministic codegen.
        if isinstance(headers_config, dict):
            normalized_headers = [
                {"key": str(key), "value": "" if value is None else str(value)}
                for key, value in headers_config.items()
            ]
        elif isinstance(headers_config, list):
            normalized_headers = []
            for item in headers_config:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key", "")).strip()
                if not key:
                    continue
                value = item.get("value", "")
                normalized_headers.append({"key": key, "value": "" if value is None else str(value)})
        else:
            normalized_headers = []

        lines = [
            "# HTTP Request",
            f"_http_method = {method!r}",
            f"_http_url_template = {url!r}",
            f"_http_headers_template = {normalized_headers!r}",
            f"_http_timeout_seconds = {timeout_seconds!r}",
            f"_http_body_raw_json = {body_raw_json!r}",
            f"_http_query_params_template = {normalized_query_params!r}",
            "_out['http_method'] = _http_method",
            "_out['http_ok'] = False",
            "_out['http_status_code'] = None",
            "_out['http_response_headers'] = {}",
            "_out['http_response_body'] = None",
            "_out['http_error_message'] = None",
            "try:",
            "    _resolved_url = _resolve_template(_http_url_template, _item)",
            "    if _http_method == 'GET' and _http_query_params_template:",
            "        _resolved_params = []",
            "        for _qp in _http_query_params_template:",
            "            _qp_key = _qp.get('key', '').strip()",
            "            if not _qp_key:",
            "                continue",
            "            _qp_val = _resolve_template(str(_qp.get('value', '')), _item)",
            "            _resolved_params.append((_qp_key, _qp_val))",
            "        if _resolved_params:",
            "            _query_txt = _urlencode(_resolved_params, doseq=True)",
            "            if '?' in _resolved_url:",
            "                _resolved_url = _resolved_url + '&' + _query_txt",
            "            else:",
            "                _resolved_url = _resolved_url + '?' + _query_txt",
            "    _validate_target_url(_resolved_url)",
            "    _resolved_headers = {}",
            "    for _hdr in _http_headers_template:",
            "        _hdr_key = _hdr.get('key', '').strip()",
            "        if not _hdr_key:",
            "            continue",
            "        _resolved_headers[_hdr_key] = _resolve_template(str(_hdr.get('value', '')), _item)",
            "",
            "    _body_obj = None",
            "    if _http_method == 'POST':",
            "        _body_template = json.loads(_http_body_raw_json)",
            "        _body_obj = _resolve_json_template(_body_template, _item)",
            "",
            "    _result = _perform_http_request(",
            "        method=_http_method,",
            "        url=_resolved_url,",
            "        headers=_resolved_headers,",
            "        body_obj=_body_obj,",
            "        timeout_seconds=_http_timeout_seconds,",
            "    )",
            "",
            "    _out['http_url_resolved'] = _resolved_url",
            "    _out['http_ok'] = _result['ok']",
            "    _out['http_status_code'] = _result['status_code']",
            "    _out['http_response_headers'] = _result['response_headers']",
            "    _out['http_response_body'] = _result['response_body']",
            "    _out['http_error_message'] = _result['error_message']",
            "except Exception as _http_ex:",
            "    _out['http_url_resolved'] = None",
            "    _out['http_ok'] = False",
            "    _out['http_status_code'] = None",
            "    _out['http_response_headers'] = {}",
            "    _out['http_response_body'] = None",
            "    _out['http_error_message'] = str(_http_ex)",
        ]

        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop("\n".join(lines), indent, include_flag)
