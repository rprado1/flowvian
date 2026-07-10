from __future__ import annotations

from app.nodes.scheduler import SchedulerNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(SchedulerNode, {"interval": 1, "unit": "seconds"})
    assert node.validate() == []


def test_validate_rejects_invalid_unit() -> None:
    node = make_node(SchedulerNode, {"interval": 1, "unit": "days"})
    errors = node.validate()
    assert_has_error(errors, "Scheduler unit must be one of")


def test_to_code_contains_loop_and_sleep_seconds() -> None:
    node = make_node(SchedulerNode, {"interval": 2, "unit": "minutes"})
    code = node.to_code()
    assert_code_has(code, "# Scheduler", "_sleep_seconds = 120.0", "while True:")


def test_loop_close_code_contains_sleep() -> None:
    node = make_node(SchedulerNode, {"interval": 1, "unit": "seconds"})
    code = node.loop_close_code()
    assert "time.sleep(_sleep_seconds)" in code
