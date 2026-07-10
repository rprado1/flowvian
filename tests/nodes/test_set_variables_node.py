from __future__ import annotations

from app.nodes.set_variables import SetVariablesNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_literal_number() -> None:
    node = make_node(
        SetVariablesNode,
        {"variables": [{"key": "age", "type": "number", "value": "25", "value_mode": "literal", "scope": "local"}]},
    )
    assert node.validate() == []


def test_validate_rejects_invalid_key() -> None:
    node = make_node(SetVariablesNode, {"variables": [{"key": "1bad", "type": "string", "value": "x"}]})
    errors = node.validate()
    assert_has_error(errors, "not a valid Python identifier")


def test_validate_rejects_invalid_path_syntax() -> None:
    node = make_node(
        SetVariablesNode,
        {"variables": [{"key": "x", "type": "string", "value_mode": "path", "value": "bad[path"}]},
    )
    errors = node.validate()
    assert_has_error(errors, "invalid path syntax")


def test_to_code_contains_expected_fragments() -> None:
    node = make_node(
        SetVariablesNode,
        {"variables": [{"key": "name", "type": "string", "value": "${user}", "value_mode": "template", "scope": "local"}]},
    )
    code = node.to_code()
    assert_code_has(code, "# Set Variables", "_sv_mode", "_resolve_template", "_items_out")
