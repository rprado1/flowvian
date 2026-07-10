from __future__ import annotations

from app.nodes.split import SplitNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(SplitNode, {"input": "${items}", "include_other_input_fields": True})
    assert node.validate() == []


def test_validate_rejects_invalid_input_placeholder() -> None:
    node = make_node(SplitNode, {"input": "items", "include_other_input_fields": True})
    errors = node.validate()
    assert_has_error(errors, "input must be a variable placeholder")


def test_to_code_contains_split_loop() -> None:
    node = make_node(SplitNode, {"input": "${items}", "include_other_input_fields": False})
    code = node.to_code()
    assert_code_has(code, "# Split", "_split_name", "_items_out.append(_out)")
