from __future__ import annotations

from app.nodes.add_time_to_date import AddTimeToDateNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(
        AddTimeToDateNode,
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


def test_validate_rejects_boolean_days() -> None:
    node = make_node(AddTimeToDateNode, {"input_var": "date_value", "days": True, "output_var": "new_date"})
    errors = node.validate()
    assert_has_error(errors, "'days' must be a number")


def test_to_code_contains_timedelta_addition() -> None:
    node = make_node(AddTimeToDateNode, {"input_var": "date_value", "days": 1, "output_var": "new_date"})
    code = node.to_code()
    assert_code_has(code, "# Add Time to Date", "timedelta(days=_atd_days", "_out['new_date']")
