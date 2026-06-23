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

        output_var = str(self.config.get("output_var", "merged_items")).strip()
        if not output_var:
            errors.append("merge: output_var cannot be empty")
        elif not output_var.isidentifier():
            errors.append(f"merge: output_var '{output_var}' is not a valid identifier")

        return errors

    def to_code(self, indent: int = 0) -> str:
        output_var = str(self.config.get("output_var", "merged_items")).strip() or "merged_items"
        lines = [
            "# Merge",
            "_merge_items_in = len(_items)",
            "_merge_list = list(_items)",
            "_merge_out = {}",
            f"_merge_out[{output_var!r}] = _merge_list",
            "_items = [_merge_out]",
            "_branch_outputs = {'output_1': _items}",
            "_node_debug = {'counts': {'items_in': _merge_items_in, 'items_out': len(_items)}}",
        ]
        return self._indent("\n".join(lines), indent)
