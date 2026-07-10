from __future__ import annotations

from app.nodes.calculator import CalculatorNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_sum() -> None:
    node = make_node(
        CalculatorNode,
        {
            "calculations": [
                {
                    "output_key": "sum_result",
                    "operation": "sum",
                    "left": "1",
                    "right": "2",
                    "value_mode_left": "literal",
                    "value_mode_right": "literal",
                }
            ],
            "include_other_input_fields": False,
        },
    )
    assert node.validate() == []


def test_validate_rejects_invalid_operation() -> None:
    node = make_node(
        CalculatorNode,
        {
            "calculations": [
                {
                    "output_key": "x",
                    "operation": "pow",
                    "left": "1",
                    "right": "2",
                }
            ]
        },
    )
    errors = node.validate()
    assert_has_error(errors, "invalid operation")


def test_to_code_contains_calculator_blocks() -> None:
    node = make_node(
        CalculatorNode,
        {
            "calculations": [
                {
                    "output_key": "sum_result",
                    "operation": "sum",
                    "left": "1",
                    "right": "2",
                }
            ]
        },
    )
    code = node.to_code()
    assert_code_has(code, "# Calculator", "_calc_op", "_calc_result", "_out[_calc_key]")
