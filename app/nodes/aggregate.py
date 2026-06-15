from app.nodes.base import BaseNode


class AggregateNode(BaseNode):
    NODE_TYPE = "aggregate"

    def validate(self) -> list[str]:
        errors: list[str] = []

        output_var = str(self.config.get("output_var", "")).strip()
        if not output_var:
            errors.append("aggregate: output_var is required")
        elif not output_var.isidentifier():
            errors.append(f"aggregate: output_var '{output_var}' is not a valid identifier")

        include_flag = self.config.get("include_other_input_fields", False)
        if not isinstance(include_flag, bool):
            errors.append("aggregate: include_other_input_fields must be a boolean")

        return errors

    def to_code(self, indent: int = 0) -> str:
        output_var = str(self.config.get("output_var", "items")).strip() or "items"
        include_flag = bool(self.config.get("include_other_input_fields", False))

        lines = [
            "# Aggregate",
            "_aggregate_items_in = len(_items)",
            "_aggregate_list = list(_items)",
        ]

        if include_flag:
            lines.extend(
                [
                    "if _items:",
                    "    _aggregate_out = dict(_items[0])",
                    "else:",
                    "    _aggregate_out = {}",
                ]
            )
        else:
            lines.append("_aggregate_out = {}")

        lines.extend(
            [
                f"_aggregate_out[{output_var!r}] = _aggregate_list",
                "_items = [_aggregate_out]",
                "_branch_outputs = {'output_1': _items}",
                "_node_debug = {'counts': {'items_in': _aggregate_items_in, 'items_out': len(_items)}}",
            ]
        )

        return self._indent("\n".join(lines), indent)
