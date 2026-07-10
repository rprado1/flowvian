from __future__ import annotations

from app.nodes.http_request import HttpRequestNode, _quote_unquoted_placeholders
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_get() -> None:
    node = make_node(
        HttpRequestNode,
        {
            "method": "GET",
            "url": "https://example.com",
            "query_params": [],
            "headers": [],
            "timeout_seconds": 30,
            "output_var": "http_result",
        },
    )
    assert node.validate() == []


def test_validate_rejects_invalid_method() -> None:
    node = make_node(HttpRequestNode, {"method": "PUT", "url": "https://example.com"})
    errors = node.validate()
    assert_has_error(errors, "method must be GET or POST")


def test_validate_post_requires_valid_body_json() -> None:
    node = make_node(HttpRequestNode, {"method": "POST", "url": "https://example.com", "body_raw_json": "{\"a\": }"})
    errors = node.validate()
    assert_has_error(errors, "body_raw_json must be valid JSON")


def test_quote_unquoted_placeholders_wraps_placeholder() -> None:
    raw = '{"x": ${USER_ID}}'
    out = _quote_unquoted_placeholders(raw)
    assert '"${USER_ID}"' in out


def test_to_code_contains_http_blocks() -> None:
    node = make_node(HttpRequestNode, {"method": "GET", "url": "https://example.com", "query_params": [], "headers": []})
    code = node.to_code()
    assert_code_has(code, "# HTTP Request", "_perform_http_request", "_http_output_var")
