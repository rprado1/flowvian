from __future__ import annotations

from app.nodes.sort import SortNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(SortNode, {"input": "${score}", "order": "asc"})
    assert node.validate() == []


def test_validate_rejects_invalid_order() -> None:
    node = make_node(SortNode, {"input": "${score}", "order": "down"})
    errors = node.validate()
    assert_has_error(errors, "order must be 'asc' or 'desc'")


def test_to_code_contains_sort_blocks() -> None:
    node = make_node(SortNode, {"input": "${score}", "order": "desc"})
    code = node.to_code()
    assert_code_has(code, "# Sort", "def _sort_key", "sorted(_items")
