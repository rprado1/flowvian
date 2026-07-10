from __future__ import annotations

from app.nodes.telegram_send_message import TelegramSendMessageNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(
        TelegramSendMessageNode,
        {
            "base_url": "https://api.telegram.org",
            "access_token": "token",
            "chat_id": "12345",
            "message": "Hello",
            "ssl_mode": "strict",
            "output_var": "telegram_result",
            "include_other_input_fields": False,
        },
    )
    assert node.validate() == []


def test_validate_rejects_invalid_ssl_mode() -> None:
    node = make_node(
        TelegramSendMessageNode,
        {
            "base_url": "https://api.telegram.org",
            "access_token": "token",
            "chat_id": "12345",
            "message": "Hello",
            "ssl_mode": "bad",
            "output_var": "telegram_result",
        },
    )
    errors = node.validate()
    assert_has_error(errors, "ssl_mode must be strict or insecure")


def test_to_code_contains_http_call() -> None:
    node = make_node(
        TelegramSendMessageNode,
        {
            "base_url": "https://api.telegram.org",
            "access_token": "token",
            "chat_id": "12345",
            "message": "Hello",
            "ssl_mode": "strict",
            "output_var": "telegram_result",
        },
    )
    code = node.to_code()
    assert_code_has(code, "# Telegram Send Message", "_perform_http_request", "_tg_output_var")
