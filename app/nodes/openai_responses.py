import json
from urllib.parse import urlparse
from typing import Any

from app.nodes.base import BaseNode


class OpenaiResponsesNode(BaseNode):
    NODE_TYPE = "openai_responses"

    _ALLOWED_ROLES = {"user", "system"}

    def _normalize_messages(self) -> tuple[list[dict[str, str]], list[str]]:
        errors: list[str] = []
        raw_message = self.config.get("message", [])

        if isinstance(raw_message, str):
            message_text = raw_message.strip()
            if not message_text:
                return [], ["openai_responses: message cannot be empty"]
            try:
                parsed = json.loads(message_text)
            except Exception:
                return [], ["openai_responses: message must be valid JSON"]
            raw_items = parsed
        else:
            raw_items = raw_message

        if not isinstance(raw_items, list):
            return [], ["openai_responses: message must be an array of {role, content}"]
        if not raw_items:
            return [], ["openai_responses: message must include at least one entry"]

        normalized: list[dict[str, str]] = []
        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                errors.append(f"openai_responses: message item {idx} must be an object")
                continue
            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()
            if role not in self._ALLOWED_ROLES:
                errors.append(f"openai_responses: message item {idx} has invalid role '{role}'")
                continue
            if not content:
                errors.append(f"openai_responses: message item {idx} content cannot be empty")
                continue
            normalized.append({"role": role, "content": content})

        return normalized, errors

    def validate(self) -> list[str]:
        errors: list[str] = []

        base_url = str(self.config.get("base_url", "")).strip()
        if not base_url:
            errors.append("openai_responses: base_url cannot be empty")
        else:
            parsed = urlparse(base_url)
            if parsed.scheme not in ("http", "https"):
                errors.append("openai_responses: base_url must start with http:// or https://")
            if not parsed.netloc:
                errors.append("openai_responses: base_url must include hostname")

        api_key = str(self.config.get("api_key", "")).strip()
        if not api_key:
            errors.append("openai_responses: api_key cannot be empty")

        model = str(self.config.get("model", "")).strip()
        if not model:
            errors.append("openai_responses: model cannot be empty")

        _, msg_errors = self._normalize_messages()
        errors.extend(msg_errors)

        instructions = str(self.config.get("instructions", "")).strip()
        if not instructions:
            errors.append("openai_responses: instructions cannot be empty")

        raw_temperature = self.config.get("temperature", 0.7)
        try:
            temp = float(raw_temperature)
            if temp < 0 or temp > 2:
                errors.append("openai_responses: temperature must be between 0 and 2")
        except (TypeError, ValueError):
            errors.append("openai_responses: temperature must be a number")

        output_var = str(self.config.get("output_var", "openai_response")).strip()
        if not output_var:
            errors.append("openai_responses: output_var cannot be empty")
        elif not output_var.isidentifier():
            errors.append(f"openai_responses: output_var '{output_var}' is not a valid Python identifier")

        include_flag = self.config.get("include_other_input_fields", False)
        if not isinstance(include_flag, bool):
            errors.append("openai_responses: include_other_input_fields must be a boolean")

        return errors

    def to_code(self, indent: int = 0) -> str:
        base_url = str(self.config.get("base_url", "https://api.openai.com/v1")).strip() or "https://api.openai.com/v1"
        api_key = str(self.config.get("api_key", "")).strip()
        model = str(self.config.get("model", "gpt-5-mini")).strip() or "gpt-5-mini"
        normalized_messages, _ = self._normalize_messages()
        instructions = str(self.config.get("instructions", "")).strip()
        temperature = float(self.config.get("temperature", 0.7) or 0.7)
        output_var = str(self.config.get("output_var", "openai_response")).strip() or "openai_response"

        lines = [
            "# OpenAI Responses",
            f"_or_base_url_t = {base_url!r}",
            f"_or_api_key_t = {api_key!r}",
            f"_or_model_t = {model!r}",
            f"_or_message_template = {normalized_messages!r}",
            f"_or_instructions_t = {instructions!r}",
            f"_or_temperature = {temperature!r}",
            f"_or_output_var = {output_var!r}",
            "_out[_or_output_var] = {'ok': False, 'status_code': None, 'response': None, 'text': None, 'error_message': None}",
            "try:",
            "    _or_base_url = _resolve_template(_or_base_url_t, _item).rstrip('/')",
            "    _or_api_key = _resolve_template(_or_api_key_t, _item).strip()",
            "    _or_model = _resolve_template(_or_model_t, _item).strip()",
            "    _or_instructions = _resolve_template(_or_instructions_t, _item)",
            "    _or_input = _resolve_json_template(_or_message_template, _item)",
            "",
            "    if not _or_base_url:",
            "        raise ValueError('openai_responses: base_url is empty after template resolution')",
            "    if not _or_api_key:",
            "        raise ValueError('openai_responses: api_key is empty after template resolution')",
            "    if not _or_model:",
            "        raise ValueError('openai_responses: model is empty after template resolution')",
            "",
            "    _or_url = _or_base_url + '/responses'",
            "    _validate_target_url(_or_url)",
            "    _or_headers = {",
            "        'Authorization': 'Bearer ' + _or_api_key,",
            "        'Content-Type': 'application/json',",
            "    }",
            "    _or_body = {",
            "        'model': _or_model,",
            "        'input': _or_input,",
            "        'instructions': _or_instructions,",
            "        'temperature': _or_temperature,",
            "    }",
            "",
            "    _or_result = _perform_http_request(",
            "        method='POST',",
            "        url=_or_url,",
            "        headers=_or_headers,",
            "        body_obj=_or_body,",
            "        timeout_seconds=60,",
            "    )",
            "",
            "    _or_text = None",
            "    _or_resp = _or_result.get('response_body')",
            "    if isinstance(_or_resp, dict):",
            "        _or_output = _or_resp.get('output')",
            "        if isinstance(_or_output, list):",
            "            _chunks = []",
            "            for _entry in _or_output:",
            "                if not isinstance(_entry, dict):",
            "                    continue",
            "                _content = _entry.get('content')",
            "                if not isinstance(_content, list):",
            "                    continue",
            "                for _part in _content:",
            "                    if not isinstance(_part, dict):",
            "                        continue",
            "                    if _part.get('type') == 'output_text':",
            "                        _txt = _part.get('text')",
            "                        if _txt is not None:",
            "                            _chunks.append(str(_txt))",
            "            if _chunks:",
            "                _or_text = ''.join(_chunks)",
            "        if _or_text is None and isinstance(_or_resp.get('output_text'), str):",
            "            _or_text = _or_resp.get('output_text')",
            "",
            "    _out[_or_output_var] = {",
            "        'ok': _or_result.get('ok'),",
            "        'status_code': _or_result.get('status_code'),",
            "        'response': _or_resp,",
            "        'text': _or_text,",
            "        'error_message': _or_result.get('error_message'),",
            "    }",
            "except Exception as _or_ex:",
            "    _out[_or_output_var] = {'ok': False, 'status_code': None, 'response': None, 'text': None, 'error_message': str(_or_ex)}",
        ]

        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop("\n".join(lines), indent, include_flag)
