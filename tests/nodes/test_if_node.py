from __future__ import annotations

from app.nodes.if_node import IfNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_condition() -> None:
    node = make_node(
        IfNode,
        {
            "conditions": [
                {
                    "input": "${status}",
                    "data_type": "string",
                    "operator": "equals",
                    "compare_value": "ok",
                    "join": "and",
                }
            ]
        },
    )
    assert node.validate() == []


def test_validate_requires_placeholder_input() -> None:
    node = make_node(
        IfNode,
        {"conditions": [{"input": "status", "data_type": "string", "operator": "equals", "compare_value": "ok"}]},
    )
    errors = node.validate()
    assert_has_error(errors, "must be a variable placeholder")


def test_validate_rejects_invalid_operator_for_type() -> None:
    node = make_node(
        IfNode,
        {"conditions": [{"input": "${a}", "data_type": "number", "operator": "contains", "compare_value": "1"}]},
    )
    errors = node.validate()
    assert_has_error(errors, "is not valid for type")


def test_to_code_contains_condition_engine() -> None:
    node = make_node(
        IfNode,
        {"conditions": [{"input": "${a}", "data_type": "number", "operator": "greater_than", "compare_value": "1"}]},
    )
    code = node.to_code()
    assert_code_has(code, "# IF", "_if_conditions", "_items_true", "_items_false", "_branch_outputs")
