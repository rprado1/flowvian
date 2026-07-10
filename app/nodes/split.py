import re

from app.nodes.base import BaseNode


class SplitNode(BaseNode):
    NODE_TYPE = "split"

    _EXACT_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")

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
            errors.append("split: input must be a variable placeholder like ${MY_ARRAY}")

        include_flag = self.config.get("include_other_input_fields", True)
        if not isinstance(include_flag, bool):
            errors.append("split: include_other_input_fields must be a boolean")

        return errors

    def to_code(self, indent: int = 0) -> str:
        input_name = self._parse_input_name(self.config.get("input", ""))
        include_flag = bool(self.config.get("include_other_input_fields", True))

        lines = [
            "# Split",
            "_items_out = []",
            "for _item in _items:",
            f"    _split_name = {input_name!r}",
            "    if _split_name not in _item:",
            "        raise ValueError(f\"split: missing variable '{_split_name}' in input item\")",
            "    _split_arr = _item.get(_split_name)",
            "    if not isinstance(_split_arr, list):",
            "        raise ValueError(f\"split: variable '{_split_name}' must be an array, got {type(_split_arr).__name__}\")",
            "    for _split_element in _split_arr:",
        ]

        if include_flag:
            lines.append("        _out = {**_item}")
            lines.append("        _out[_split_name] = _split_element")
        else:
            lines.append("        _out = {_split_name: _split_element}")

        lines.append("        _items_out.append(_out)")
        lines.append("_items = _items_out")

        return self._indent("\n".join(lines), indent)
