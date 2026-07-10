from __future__ import annotations

from app.nodes.stop_and_error import StopAndErrorNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_message() -> None:
    node = make_node(StopAndErrorNode, {"message": "Stop now"})
    assert node.validate() == []


def test_validate_requires_message() -> None:
    node = make_node(StopAndErrorNode, {"message": ""})
    errors = node.validate()
    assert_has_error(errors, "'message' is required")


def test_to_code_contains_stop_exception() -> None:
    node = make_node(StopAndErrorNode, {"message": "Stop now"})
    code = node.to_code()
    assert_code_has(code, "# Stop and Error", "_StopIterationExecution", "_resolve_template")
