from __future__ import annotations

from app.nodes.merge import MergeNode
from tests.helpers import assert_code_has, assert_has_error, make_node


def test_validate_accepts_valid_config() -> None:
    node = make_node(MergeNode, {"strategy": "append", "branch_count": 2, "output_var": "merged_items"})
    assert node.validate() == []


def test_validate_rejects_invalid_branch_count() -> None:
    node = make_node(MergeNode, {"strategy": "append", "branch_count": 1, "output_var": "merged_items"})
    errors = node.validate()
    assert_has_error(errors, "branch_count must be an integer greater than or equal to 2")


def test_to_code_contains_merge_blocks() -> None:
    node = make_node(MergeNode, {"strategy": "append", "branch_count": 2, "output_var": "merged_items"})
    code = node.to_code()
    assert_code_has(code, "# Merge", "_merge_list = list(_items)", "_branch_outputs")
