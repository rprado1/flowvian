from __future__ import annotations

from app.nodes.map import MapNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_map_rule() -> None:
    node = make_node(
        MapNode,
        {
            "output_key": "mapped",
            "input_value_mode": "variable",
            "input_source": "${status}",
            "input_data_type": "string",
            "rules": [
                {
                    "operator": "equals",
                    "compare_value": "ok",
                    "value_mode": "literal",
                    "mapped_value": "SUCCESS",
                }
            ],
            "default": {"value_mode": "literal", "mapped_value": "UNKNOWN"},
            "include_other_input_fields": False,
        },
    )
    assert node.validate() == []


def test_validate_rejects_empty_rules() -> None:
    node = make_node(
        MapNode,
        {
            "output_key": "mapped",
            "input_value_mode": "variable",
            "input_source": "${status}",
            "input_data_type": "string",
            "rules": [],
        },
    )
    errors = node.validate()
    assert_has_error(errors, "rules must be a non-empty list")


def test_to_code_contains_map_blocks() -> None:
    node = make_node(
        MapNode,
        {
            "output_key": "mapped",
            "input_value_mode": "variable",
            "input_source": "${status}",
            "input_data_type": "string",
            "rules": [{"operator": "equals", "compare_value": "ok", "value_mode": "literal", "mapped_value": "SUCCESS"}],
            "default": {"value_mode": "literal", "mapped_value": "UNKNOWN"},
        },
    )
    code = node.to_code()
    assert_code_has(code, "# MAP", "_map_rules", "_map_output_key", "_out[_map_output_key]")
