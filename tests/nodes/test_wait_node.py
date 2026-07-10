from __future__ import annotations

from app.nodes.wait import WaitNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_seconds() -> None:
    node = make_node(WaitNode, {"seconds": 1})
    assert node.validate() == []


def test_validate_rejects_non_numeric_seconds() -> None:
    node = make_node(WaitNode, {"seconds": "abc"})
    errors = node.validate()
    assert_has_error(errors, "seconds must be a number")


def test_to_code_contains_sleep_call() -> None:
    node = make_node(WaitNode, {"seconds": 2})
    code = node.to_code()
    assert_code_has(code, "# Wait", "time.sleep(2.0)")
