from __future__ import annotations

from app.nodes.filter import FilterNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_condition() -> None:
    node = make_node(
        FilterNode,
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


def test_validate_rejects_missing_placeholder() -> None:
    node = make_node(
        FilterNode,
        {"conditions": [{"input": "status", "data_type": "string", "operator": "equals", "compare_value": "ok"}]},
    )
    errors = node.validate()
    assert_has_error(errors, "must be a variable placeholder")


def test_to_code_contains_filter_blocks() -> None:
    node = make_node(
        FilterNode,
        {"conditions": [{"input": "${a}", "data_type": "number", "operator": "greater_than", "compare_value": "1"}]},
    )
    code = node.to_code()
    assert_code_has(code, "# FILTER", "_filter_conditions", "_items_filtered", "_branch_outputs")
