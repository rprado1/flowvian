from __future__ import annotations

from app.nodes.base import BaseNode


class MergeNode(BaseNode):
    NODE_TYPE = "merge"

    def validate(self) -> list[str]:
        errors: list[str] = []
        strategy = self.config.get("strategy", "append")
        if strategy not in ("append",):
            errors.append(f"merge: unknown strategy '{strategy}'")
        return errors

    def to_code(self, indent: int = 0) -> str:
        code_body = "# Merge: append items from all inbound branches\npass"
        return self._indent(code_body, indent)
