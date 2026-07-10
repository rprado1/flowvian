from __future__ import annotations

from urllib.parse import urlparse

from app.nodes.base import BaseNode


class TelegramSendMessageNode(BaseNode):
    NODE_TYPE = "telegram_send_message"

    def validate(self) -> list[str]:
        errors: list[str] = []

        base_url = str(self.config.get("base_url", "")).strip()
        if not base_url:
            errors.append("telegram_send_message: base_url cannot be empty")
        else:
            parsed = urlparse(base_url)
            if parsed.scheme not in ("http", "https"):
                errors.append("telegram_send_message: base_url must start with http:// or https://")
            if not parsed.netloc:
                errors.append("telegram_send_message: base_url must include hostname")

        access_token = str(self.config.get("access_token", "")).strip()
        if not access_token:
            errors.append("telegram_send_message: access_token cannot be empty")

        chat_id = str(self.config.get("chat_id", "")).strip()
        if not chat_id:
            errors.append("telegram_send_message: chat_id cannot be empty (recommended: ${TELEGRAM_CHAT_ID})")

        message = str(self.config.get("message", "")).strip()
        if not message:
            errors.append("telegram_send_message: message cannot be empty")

        ssl_mode = str(self.config.get("ssl_mode", "strict")).strip().lower() or "strict"
        if ssl_mode not in ("strict", "insecure"):
            errors.append("telegram_send_message: ssl_mode must be strict or insecure")

        output_var = str(self.config.get("output_var", "telegram_result")).strip()
        if not output_var:
            errors.append("telegram_send_message: output_var cannot be empty")
        elif not output_var.isidentifier():
            errors.append(
                f"telegram_send_message: output_var '{output_var}' is not a valid Python identifier"
            )

        include_flag = self.config.get("include_other_input_fields", False)
        if not isinstance(include_flag, bool):
            errors.append("telegram_send_message: include_other_input_fields must be a boolean")

        return errors

    def to_code(self, indent: int = 0) -> str:
        base_url = str(self.config.get("base_url", "https://api.telegram.org")).strip() or "https://api.telegram.org"
        access_token = str(self.config.get("access_token", "")).strip()
        chat_id = str(self.config.get("chat_id", "${TELEGRAM_CHAT_ID}")).strip() or "${TELEGRAM_CHAT_ID}"
        message = str(self.config.get("message", "")).strip()
        disable_notification = bool(self.config.get("disable_notification", False))
        ssl_mode = str(self.config.get("ssl_mode", "strict")).strip().lower() or "strict"
        output_var = str(self.config.get("output_var", "telegram_result")).strip() or "telegram_result"

        lines = [
            "# Telegram Send Message",
            f"_tg_base_url_t = {base_url!r}",
            f"_tg_access_token_t = {access_token!r}",
            f"_tg_chat_id_t = {chat_id!r}",
            f"_tg_message_t = {message!r}",
            f"_tg_disable_notification = {disable_notification!r}",
            f"_tg_ssl_mode = {ssl_mode!r}",
            f"_tg_output_var = {output_var!r}",
            "_out[_tg_output_var] = {'ok': False, 'status_code': None, 'telegram_ok': None, 'message_id': None, 'chat_id': None, 'response': None, 'error_message': None, 'tls_mode': _tg_ssl_mode}",
            "try:",
            "    _tg_base_url = _resolve_template(_tg_base_url_t, _item).rstrip('/')",
            "    _tg_access_token = _resolve_template(_tg_access_token_t, _item).strip()",
            "    _tg_chat_id = _resolve_template(_tg_chat_id_t, _item).strip()",
            "    _tg_message = _resolve_template(_tg_message_t, _item)",
            "",
            "    if not _tg_base_url:",
            "        raise ValueError('telegram_send_message: base_url is empty after template resolution')",
            "    if not _tg_access_token:",
            "        raise ValueError('telegram_send_message: access_token is empty after template resolution')",
            "    if not _tg_chat_id:",
            "        raise ValueError('Missing Telegram chat id: set chat_id (recommended: ${TELEGRAM_CHAT_ID})')",
            "    if _tg_message is None or str(_tg_message).strip() == '':",
            "        raise ValueError('telegram_send_message: message is empty after template resolution')",
            "",
            "    _tg_url = _tg_base_url + '/bot' + _tg_access_token + '/sendMessage'",
            "    _validate_target_url(_tg_url)",
            "    _tg_headers = {'Content-Type': 'application/json'}",
            "    _tg_body = {'chat_id': _tg_chat_id, 'text': str(_tg_message)}",
            "    if _tg_disable_notification:",
            "        _tg_body['disable_notification'] = True",
            "",
            "    _tg_result = _perform_http_request(",
            "        method='POST',",
            "        url=_tg_url,",
            "        headers=_tg_headers,",
            "        body_obj=_tg_body,",
            "        timeout_seconds=60,",
            "        ssl_mode=_tg_ssl_mode,",
            "    )",
            "",
            "    _tg_response = _tg_result.get('response_body')",
            "    _tg_telegram_ok = None",
            "    _tg_message_id = None",
            "    _tg_chat_id_resp = _tg_chat_id",
            "    _tg_error = _tg_result.get('error_message')",
            "",
            "    if isinstance(_tg_response, dict):",
            "        if isinstance(_tg_response.get('ok'), bool):",
            "            _tg_telegram_ok = _tg_response.get('ok')",
            "        _tg_result_obj = _tg_response.get('result')",
            "        if isinstance(_tg_result_obj, dict):",
            "            _msg_id_val = _tg_result_obj.get('message_id')",
            "            if isinstance(_msg_id_val, int):",
            "                _tg_message_id = _msg_id_val",
            "            _chat_obj = _tg_result_obj.get('chat')",
            "            if isinstance(_chat_obj, dict) and _chat_obj.get('id') is not None:",
            "                _tg_chat_id_resp = _chat_obj.get('id')",
            "",
            "        if _tg_error is None and _tg_telegram_ok is False:",
            "            _desc = _tg_response.get('description')",
            "            if _desc is not None:",
            "                _tg_error = str(_desc)",
            "            else:",
            "                _tg_error = 'Telegram API returned ok=false'",
            "",
            "    _tg_ok = bool(_tg_result.get('ok')) and (_tg_telegram_ok is not False)",
            "    _out[_tg_output_var] = {",
            "        'ok': _tg_ok,",
            "        'status_code': _tg_result.get('status_code'),",
            "        'telegram_ok': _tg_telegram_ok,",
            "        'message_id': _tg_message_id,",
            "        'chat_id': _tg_chat_id_resp,",
            "        'response': _tg_response,",
            "        'error_message': _tg_error,",
            "        'tls_mode': _tg_ssl_mode,",
            "    }",
            "except Exception as _tg_ex:",
            "    _out[_tg_output_var] = {'ok': False, 'status_code': None, 'telegram_ok': None, 'message_id': None, 'chat_id': None, 'response': None, 'error_message': str(_tg_ex), 'tls_mode': _tg_ssl_mode}",
        ]

        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop("\n".join(lines), indent, include_flag)
