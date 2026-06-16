from app.nodes.base import BaseNode
import re


class SortNode(BaseNode):
    NODE_TYPE = "sort"
    _EXACT_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")

    @staticmethod
    def _normalize_order(raw_order) -> str:
        order = str(raw_order or "asc").strip().lower()
        return "desc" if order == "desc" else "asc"

    @classmethod
    def _parse_input_name(cls, raw_input) -> str:
        text = str(raw_input or "").strip()
        match = cls._EXACT_PLACEHOLDER_RE.fullmatch(text)
        if not match:
            return ""
        return match.group(1)

    def validate(self) -> list[str]:
        errors: list[str] = []

        input_name = self._parse_input_name(self.config.get("input", ""))
        if not input_name:
            errors.append("sort: input must be a variable placeholder like ${VARNAME}")

        raw_order = str(self.config.get("order", "asc")).strip().lower()
        if raw_order not in ("asc", "desc"):
            errors.append(f"sort: order must be 'asc' or 'desc', got '{raw_order}'")

        return errors

    def to_code(self, indent: int = 0) -> str:
        input_name = self._parse_input_name(self.config.get("input", ""))
        order = self._normalize_order(self.config.get("order", "asc"))

        lines = [
            "# Sort",
            f"_sort_input_name = {input_name!r}",
            f"_sort_order = {order!r}",
            "_sort_items_in = len(_items)",
            "",
            "def _sort_key(_item):",
            "    if _sort_input_name not in _item:",
            "        raise ValueError(f\"sort: missing variable '{_sort_input_name}' in input item\")",
            "    _value = _item.get(_sort_input_name)",
            "",
            "    if _value is None:",
            "        return (0, '')",
            "    if isinstance(_value, bool):",
            "        return (1, int(_value))",
            "    if isinstance(_value, (int, float)):",
            "        return (2, float(_value))",
            "    if isinstance(_value, str):",
            "        return (3, _value)",
            "    if isinstance(_value, list):",
            "        return (4, repr(_value))",
            "    if isinstance(_value, dict):",
            "        return (5, repr(sorted(_value.items(), key=lambda _pair: str(_pair[0]))))",
            "    return (6, repr(_value))",
            "",
            "_items = sorted(_items, key=_sort_key, reverse=(_sort_order == 'desc'))",
            "_branch_outputs = {'output_1': _items}",
            "_node_debug = {'sort': {'input': '${' + _sort_input_name + '}', 'order': _sort_order, 'items_in': _sort_items_in, 'items_out': len(_items)}}",
        ]

        return self._indent("\n".join(lines), indent)
