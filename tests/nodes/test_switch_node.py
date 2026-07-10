from __future__ import annotations

from app.nodes.switch import SwitchNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_route() -> None:
    node = make_node(
        SwitchNode,
        {
            "routes": [
                {
                    "name": "Route 1",
                    "condition": {
                        "input": "${status}",
                        "data_type": "string",
                        "operator": "equals",
                        "compare_value": "ok",
                    },
                }
            ],
            "discard_unmatched": True,
        },
    )
    assert node.validate() == []


def test_validate_rejects_invalid_input_reference() -> None:
    node = make_node(
        SwitchNode,
        {
            "routes": [
                {
                    "name": "Route 1",
                    "condition": {
                        "input": "status",
                        "data_type": "string",
                        "operator": "equals",
                        "compare_value": "ok",
                    },
                }
            ]
        },
    )
    errors = node.validate()
    assert_has_error(errors, "input must be a variable placeholder")


def test_to_code_contains_switch_blocks() -> None:
    node = make_node(
        SwitchNode,
        {
            "routes": [
                {
                    "name": "Route 1",
                    "condition": {
                        "input": "${status}",
                        "data_type": "string",
                        "operator": "equals",
                        "compare_value": "ok",
                    },
                }
            ]
        },
    )
    code = node.to_code()
    assert_code_has(code, "# SWITCH", "_switch_routes", "_branch_outputs", "_switch_unmatched")
