from __future__ import annotations


def make_node(node_cls, config=None, node_id="n1"):
    return node_cls(node_id=node_id, config=config or {})


def assert_code_has(code: str, *fragments: str) -> None:
    for fragment in fragments:
        assert fragment in code, f"Missing fragment: {fragment}"


def assert_has_error(errors: list[str], text: str) -> None:
    assert any(text in err for err in errors), f"Expected '{text}' in {errors}"
