from __future__ import annotations

from app.nodes.openai_responses import OpenaiResponsesNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_min_valid_config() -> None:
    node = make_node(
        OpenaiResponsesNode,
        {
            "base_url": "https://api.openai.com/v1",
            "api_key": "test_key",
            "model": "gpt-5-mini",
            "message": [{"role": "user", "content": "Hello"}],
            "instructions": "Short reply",
            "temperature": 0.7,
            "output_var": "openai_response",
            "include_other_input_fields": False,
        },
    )
    assert node.validate() == []


def test_validate_rejects_invalid_temperature() -> None:
    node = make_node(
        OpenaiResponsesNode,
        {
            "base_url": "https://api.openai.com/v1",
            "api_key": "test_key",
            "model": "gpt-5-mini",
            "message": [{"role": "user", "content": "Hello"}],
            "instructions": "Short reply",
            "temperature": 4,
            "output_var": "openai_response",
        },
    )
    errors = node.validate()
    assert_has_error(errors, "temperature must be between 0 and 2")


def test_to_code_contains_http_request_flow() -> None:
    node = make_node(
        OpenaiResponsesNode,
        {
            "base_url": "https://api.openai.com/v1",
            "api_key": "test_key",
            "model": "gpt-5-mini",
            "message": [{"role": "user", "content": "Hello"}],
            "instructions": "Short reply",
            "temperature": 0.7,
            "output_var": "openai_response",
        },
    )
    code = node.to_code()
    assert_code_has(code, "# OpenAI Responses", "_perform_http_request", "_or_output_var")
