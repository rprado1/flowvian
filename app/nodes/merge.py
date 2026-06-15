from __future__ import annotations

from app.nodes.base import BaseNode


class MergeNode(BaseNode):
    NODE_TYPE = "merge"

    def validate(self) -> list[str]:
        errors: list[str] = []
        strategy = self.config.get("strategy", "append")
        if strategy not in ("append",):
            errors.append(f"merge: unknown strategy '{strategy}'")

        branch_count_raw = self.config.get("branch_count", 2)
        try:
            branch_count = int(branch_count_raw)
            if branch_count < 2:
                errors.append("merge: branch_count must be an integer greater than or equal to 2")
        except (TypeError, ValueError):
            errors.append("merge: branch_count must be an integer")

        return errors

    def to_code(self, indent: int = 0) -> str:
        code_body = "# Merge: append items from all inbound branches\npass"
        return self._indent(code_body, indent)
