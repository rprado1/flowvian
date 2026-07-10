from __future__ import annotations

from app.nodes.subtract_time_from_date import SubtractTimeFromDateNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(
        SubtractTimeFromDateNode,
        {
            "input_var": "date_value",
            "days": 1,
            "hours": 0,
            "minutes": 0,
            "seconds": 0,
            "output_var": "new_date",
        },
    )
    assert node.validate() == []


def test_validate_rejects_boolean_hours() -> None:
    node = make_node(SubtractTimeFromDateNode, {"input_var": "date_value", "hours": True, "output_var": "new_date"})
    errors = node.validate()
    assert_has_error(errors, "'hours' must be a number")


def test_to_code_contains_timedelta_subtraction() -> None:
    node = make_node(SubtractTimeFromDateNode, {"input_var": "date_value", "days": 1, "output_var": "new_date"})
    code = node.to_code()
    assert_code_has(code, "# Subtract Time from Date", "timedelta(days=_std_days", "_out['new_date']")
