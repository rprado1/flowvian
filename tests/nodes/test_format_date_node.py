from __future__ import annotations

from app.nodes.format_date import FormatDateNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(
        FormatDateNode,
        {
            "input": "${date_value}",
            "format": "iso_8601",
            "output_var": "formatted_date",
            "include_other_input_fields": False,
        },
    )
    assert node.validate() == []


def test_validate_rejects_unsupported_format() -> None:
    node = make_node(FormatDateNode, {"input": "${date_value}", "format": "custom", "output_var": "formatted_date"})
    errors = node.validate()
    assert_has_error(errors, "unsupported format")


def test_to_code_contains_format_logic() -> None:
    node = make_node(FormatDateNode, {"input": "${date_value}", "format": "unix_timestamp", "output_var": "formatted_date"})
    code = node.to_code()
    assert_code_has(code, "# Format Date", "_fd_format", "_out[_fd_output_var]")
