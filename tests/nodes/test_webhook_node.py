from __future__ import annotations

from app.nodes.webhook import WebhookNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_webhook() -> None:
    node = make_node(
        WebhookNode,
        {"method": "POST", "host": "0.0.0.0", "port": 8000, "path": "/hook", "input_params": []},
    )
    assert node.validate() == []


def test_validate_rejects_invalid_port() -> None:
    node = make_node(WebhookNode, {"method": "POST", "port": 70000, "path": "/hook"})
    errors = node.validate()
    assert_has_error(errors, "port must be between 1 and 65535")


def test_validate_rejects_duplicate_param_names() -> None:
    node = make_node(
        WebhookNode,
        {
            "input_params": [
                {"name": "id", "type": "string", "source": "query"},
                {"name": "id", "type": "string", "source": "query"},
            ]
        },
    )
    errors = node.validate()
    assert_has_error(errors, "duplicated input param name")


def test_to_code_contains_serve_webhook_call() -> None:
    node = make_node(WebhookNode, {"path": "/hook", "input_params": []})
    code = node.to_code()
    assert_code_has(code, "# WEBHOOK", "_serve_webhook(", "_webhook_path")
