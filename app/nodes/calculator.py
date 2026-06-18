from __future__ import annotations

import re

from app.nodes.base import BaseNode


class CalculatorNode(BaseNode):
    NODE_TYPE = "calculator"

    _ALLOWED_OPERATIONS = {
        "sum",
        "subtract",
        "multiply",
        "divide",
        "abs",
        "max",
        "min",
        "floor",
        "ceil",
        "x2",
    }
    _UNARY_OPERATIONS = {"abs", "floor", "ceil", "x2"}
    _PLACEHOLDER_RE = re.compile(r"(\$\{[A-Za-z_][A-Za-z0-9_]*\}|#\{[A-Za-z_][A-Za-z0-9_]*\})")

    @classmethod
    def _is_unary_operation(cls, operation: str) -> bool:
        return operation in cls._UNARY_OPERATIONS

    @classmethod
    def _contains_placeholder(cls, value) -> bool:
        return isinstance(value, str) and cls._PLACEHOLDER_RE.search(value) is not None

    @classmethod
    def _normalize_mode(cls, raw_mode, raw_value) -> str:
        if raw_mode is None:
            return "template" if cls._contains_placeholder(raw_value) else "literal"
        mode = str(raw_mode).strip().lower()
        if mode in ("literal", "template"):
            return mode
        return "literal"

    @staticmethod
    def _parse_number(value):
        if isinstance(value, bool):
            raise ValueError("boolean is not a valid number")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value) if value.is_integer() else value

        text = str(value).strip()
        if not text:
            raise ValueError("empty number")
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)

        num = float(text)
        return int(num) if num.is_integer() else num

    def validate(self) -> list[str]:
        errors = []
        calculations = self.config.get("calculations", [])
        if not isinstance(calculations, list):
            errors.append("calculator: 'calculations' must be a list")
            return errors

        for i, item in enumerate(calculations):
            if not isinstance(item, dict):
                errors.append(f"calculator: item {i} must be an object")
                continue

            output_key = str(item.get("output_key", "")).strip()
            if not output_key:
                errors.append(f"calculator: item {i} has an empty output_key")
            elif not output_key.isidentifier():
                errors.append(f"calculator: output_key '{output_key}' is not a valid Python identifier")

            operation = str(item.get("operation", "sum")).strip().lower()
            if operation not in self._ALLOWED_OPERATIONS:
                errors.append(f"calculator: item {i} has invalid operation '{operation}'")
                continue

            left_raw = item.get("left", "")
            right_raw = item.get("right", "")
            left_mode = self._normalize_mode(item.get("value_mode_left"), left_raw)
            right_mode = self._normalize_mode(item.get("value_mode_right"), right_raw)

            if left_mode not in ("literal", "template"):
                errors.append(f"calculator: item {i} has invalid value_mode_left '{left_mode}'")
                continue
            if right_mode not in ("literal", "template"):
                errors.append(f"calculator: item {i} has invalid value_mode_right '{right_mode}'")
                continue

            left_text = "" if left_raw is None else str(left_raw).strip()
            right_text = "" if right_raw is None else str(right_raw).strip()

            if not left_text:
                errors.append(f"calculator: item {i} requires left operand")

            if self._is_unary_operation(operation):
                if left_mode == "literal" and left_text:
                    try:
                        self._parse_number(left_raw)
                    except Exception:
                        errors.append(f"calculator: item {i} left value '{left_raw}' is not a valid number")
                continue

            if not right_text:
                errors.append(f"calculator: item {i} requires right operand for operation '{operation}'")

            if left_mode == "literal" and left_text:
                try:
                    self._parse_number(left_raw)
                except Exception:
                    errors.append(f"calculator: item {i} left value '{left_raw}' is not a valid number")

            if right_mode == "literal" and right_text:
                try:
                    self._parse_number(right_raw)
                except Exception:
                    errors.append(f"calculator: item {i} right value '{right_raw}' is not a valid number")

        include_flag = self.config.get("include_other_input_fields", False)
        if not isinstance(include_flag, bool):
            errors.append("calculator: include_other_input_fields must be a boolean")

        return errors

    def to_code(self, indent: int = 0) -> str:
        calculations = self.config.get("calculations", [])
        if not calculations:
            code_body = "# calculator: no calculations defined\npass"
        else:
            lines = ["# Calculator"]
            for item in calculations:
                output_key = str(item.get("output_key", "")).strip()
                operation = str(item.get("operation", "sum")).strip().lower() or "sum"
                left_raw = "" if item.get("left") is None else str(item.get("left"))
                right_raw = "" if item.get("right") is None else str(item.get("right"))
                left_mode = self._normalize_mode(item.get("value_mode_left"), left_raw)
                right_mode = self._normalize_mode(item.get("value_mode_right"), right_raw)

                lines.append(f"_calc_key = {output_key!r}")
                lines.append(f"_calc_op = {operation!r}")
                lines.append(f"_calc_left_raw = {left_raw!r}")
                lines.append(f"_calc_right_raw = {right_raw!r}")
                lines.append(f"_calc_left_mode = {left_mode!r}")
                lines.append(f"_calc_right_mode = {right_mode!r}")

                lines.append("if _calc_left_mode == 'template':")
                lines.append("    _calc_left_src = _resolve_template(_calc_left_raw, _item)")
                lines.append("else:")
                lines.append("    _calc_left_src = _calc_left_raw")

                lines.append("if isinstance(_calc_left_src, bool):")
                lines.append("    raise ValueError(f\"calculator: output '{_calc_key}' left operand must be numeric\")")
                lines.append("if isinstance(_calc_left_src, int):")
                lines.append("    _calc_left = _calc_left_src")
                lines.append("elif isinstance(_calc_left_src, float):")
                lines.append("    _calc_left = int(_calc_left_src) if _calc_left_src.is_integer() else _calc_left_src")
                lines.append("else:")
                lines.append("    _calc_left_txt = str(_calc_left_src).strip()")
                lines.append("    if not _calc_left_txt:")
                lines.append("        raise ValueError(f\"calculator: output '{_calc_key}' left operand is empty\")")
                lines.append("    if _calc_left_txt.isdigit() or (_calc_left_txt.startswith('-') and _calc_left_txt[1:].isdigit()):")
                lines.append("        _calc_left = int(_calc_left_txt)")
                lines.append("    else:")
                lines.append("        _calc_left_num = float(_calc_left_txt)")
                lines.append("        _calc_left = int(_calc_left_num) if _calc_left_num.is_integer() else _calc_left_num")

                lines.append("if _calc_op in ('sum', 'subtract', 'multiply', 'divide', 'max', 'min'):")
                lines.append("    if _calc_right_mode == 'template':")
                lines.append("        _calc_right_src = _resolve_template(_calc_right_raw, _item)")
                lines.append("    else:")
                lines.append("        _calc_right_src = _calc_right_raw")
                lines.append("    if isinstance(_calc_right_src, bool):")
                lines.append("        raise ValueError(f\"calculator: output '{_calc_key}' right operand must be numeric\")")
                lines.append("    if isinstance(_calc_right_src, int):")
                lines.append("        _calc_right = _calc_right_src")
                lines.append("    elif isinstance(_calc_right_src, float):")
                lines.append("        _calc_right = int(_calc_right_src) if _calc_right_src.is_integer() else _calc_right_src")
                lines.append("    else:")
                lines.append("        _calc_right_txt = str(_calc_right_src).strip()")
                lines.append("        if not _calc_right_txt:")
                lines.append("            raise ValueError(f\"calculator: output '{_calc_key}' right operand is empty\")")
                lines.append("        if _calc_right_txt.isdigit() or (_calc_right_txt.startswith('-') and _calc_right_txt[1:].isdigit()):")
                lines.append("            _calc_right = int(_calc_right_txt)")
                lines.append("        else:")
                lines.append("            _calc_right_num = float(_calc_right_txt)")
                lines.append("            _calc_right = int(_calc_right_num) if _calc_right_num.is_integer() else _calc_right_num")

                lines.append("if _calc_op == 'sum':")
                lines.append("    _calc_result = _calc_left + _calc_right")
                lines.append("elif _calc_op == 'subtract':")
                lines.append("    _calc_result = _calc_left - _calc_right")
                lines.append("elif _calc_op == 'multiply':")
                lines.append("    _calc_result = _calc_left * _calc_right")
                lines.append("elif _calc_op == 'divide':")
                lines.append("    if _calc_right == 0:")
                lines.append("        raise ValueError(f\"calculator: output '{_calc_key}' division by zero\")")
                lines.append("    _calc_result = _calc_left / _calc_right")
                lines.append("elif _calc_op == 'abs':")
                lines.append("    _calc_result = abs(_calc_left)")
                lines.append("elif _calc_op == 'max':")
                lines.append("    _calc_result = max(_calc_left, _calc_right)")
                lines.append("elif _calc_op == 'min':")
                lines.append("    _calc_result = min(_calc_left, _calc_right)")
                lines.append("elif _calc_op == 'floor':")
                lines.append("    _calc_result = math.floor(_calc_left)")
                lines.append("elif _calc_op == 'ceil':")
                lines.append("    _calc_result = math.ceil(_calc_left)")
                lines.append("elif _calc_op == 'x2':")
                lines.append("    _calc_result = _calc_left * 2")
                lines.append("else:")
                lines.append("    raise ValueError(f\"calculator: unsupported operation '{_calc_op}'\")")
                lines.append("_out[_calc_key] = _calc_result")
            code_body = "\n".join(lines)

        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop(code_body, indent, include_flag)
