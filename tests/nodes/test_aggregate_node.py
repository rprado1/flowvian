from __future__ import annotations

from app.nodes.aggregate import AggregateNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(AggregateNode, {"output_var": "items", "include_other_input_fields": False})
    assert node.validate() == []


def test_validate_rejects_empty_output_var() -> None:
    node = make_node(AggregateNode, {"output_var": "", "include_other_input_fields": False})
    errors = node.validate()
    assert_has_error(errors, "output_var is required")


def test_to_code_contains_aggregate_blocks() -> None:
    node = make_node(AggregateNode, {"output_var": "items", "include_other_input_fields": True})
    code = node.to_code()
    assert_code_has(code, "# Aggregate", "_aggregate_list", "_branch_outputs")
