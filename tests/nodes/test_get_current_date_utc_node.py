from __future__ import annotations

from app.nodes.get_current_date import GetCurrentDateUTCNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(GetCurrentDateUTCNode, {"output_var": "current_date_utc"})
    assert node.validate() == []


def test_validate_rejects_invalid_output_var() -> None:
    node = make_node(GetCurrentDateUTCNode, {"output_var": "1bad"})
    errors = node.validate()
    assert_has_error(errors, "is not a valid Python identifier")


def test_to_code_contains_utc_now_assignment() -> None:
    node = make_node(GetCurrentDateUTCNode, {"output_var": "current_date_utc"})
    code = node.to_code()
    assert_code_has(code, "# Get Current Date UTC", "datetime.now(timezone.utc).isoformat()")
