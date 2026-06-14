import json
import re

from app.nodes.base import BaseNode


class SetVariablesNode(BaseNode):
    """
    Sets one or more variables into the workflow context.

    Config:
        variables (list[{key: str, value: str}]): pairs to assign
    """

    NODE_TYPE = "set_variables"
    _TPL_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

    @staticmethod
    def _normalize_type(raw_type) -> str:
        if raw_type is None:
            return "string"
        value = str(raw_type).strip().lower()
        return value or "string"

    @classmethod
    def _is_exact_placeholder(cls, value) -> bool:
        return isinstance(value, str) and cls._TPL_VAR_RE.fullmatch(value.strip()) is not None

    @classmethod
    def _contains_placeholder(cls, value) -> bool:
        return isinstance(value, str) and cls._TPL_VAR_RE.search(value) is not None

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

    @staticmethod
    def _parse_boolean(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)

        text = str(value).strip().lower()
        if text in ("true", "1"):
            return True
        if text in ("false", "0"):
            return False
        raise ValueError("invalid boolean")

    @staticmethod
    def _parse_array(value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = json.loads(str(value))
        if not isinstance(parsed, list):
            raise ValueError("array root must be a list")
        return parsed

    def validate(self) -> list[str]:
        errors = []
        variables = self.config.get("variables", [])
        if not isinstance(variables, list):
            errors.append("set_variables: 'variables' must be a list")
            return errors
        for i, item in enumerate(variables):
            if not isinstance(item, dict):
                errors.append(f"set_variables: item {i} must be an object with 'key' and 'value'")
                continue
            key = item.get("key", "").strip()
            if not key:
                errors.append(f"set_variables: item {i} has an empty key")
            elif not key.isidentifier():
                errors.append(f"set_variables: key '{key}' is not a valid Python identifier")

            var_type = self._normalize_type(item.get("type", "string"))
            if var_type not in ("string", "number", "boolean", "array"):
                errors.append(f"set_variables: item {i} has invalid type '{var_type}'")
                continue

            value = item.get("value", "")
            if var_type == "number":
                if self._contains_placeholder(value):
                    continue
                try:
                    self._parse_number(value)
                except Exception:
                    errors.append(f"set_variables: item {i} value '{value}' is not a valid number")
            elif var_type == "boolean":
                if self._contains_placeholder(value):
                    continue
                try:
                    self._parse_boolean(value)
                except Exception:
                    errors.append(f"set_variables: item {i} value '{value}' is not a valid boolean")
            elif var_type == "array":
                if self._contains_placeholder(value):
                    continue
                try:
                    self._parse_array(value)
                except Exception:
                    errors.append(f"set_variables: item {i} value must be a valid JSON array")
        # Accept include_other_input_fields (default False)
        return errors

    def to_code(self, indent: int = 0) -> str:
        variables = self.config.get("variables", [])
        if not variables:
            code_body = "# set_variables: no variables defined\npass"
        else:
            lines = ["# Set Variables"]
            for item in variables:
                key = item.get("key", "").strip()
                value = item.get("value", "")
                var_type = self._normalize_type(item.get("type", "string"))
                raw_value = "" if value is None else str(value)
                missing_var_msg = f"set_variables: key '{key}' references missing variable "

                lines.append(f"_sv_key = {repr(key)}")
                lines.append(f"_sv_type = {repr(var_type)}")
                lines.append(f"_sv_raw = {repr(raw_value)}")
                lines.append("if _sv_type == 'string':")
                lines.append("    _out[_sv_key] = _resolve_template(_sv_raw, _item)")
                lines.append("elif _sv_type == 'number':")
                lines.append("    _sv_m = _TPL_VAR_RE.fullmatch(_sv_raw)")
                lines.append("    if _sv_m:")
                lines.append("        _sv_name = _sv_m.group(1)")
                lines.append("        if _sv_name not in _item:")
                lines.append("            raise ValueError(" + repr(missing_var_msg) + " + _sv_name)")
                lines.append("        _sv_src = _item.get(_sv_name)")
                lines.append("    else:")
                lines.append("        _sv_src = _resolve_template(_sv_raw, _item)")
                lines.append("    if isinstance(_sv_src, bool):")
                lines.append("        raise ValueError(f\"set_variables: key '{_sv_key}' expected number, got boolean\")")
                lines.append("    if isinstance(_sv_src, int):")
                lines.append("        _out[_sv_key] = _sv_src")
                lines.append("    elif isinstance(_sv_src, float):")
                lines.append("        _out[_sv_key] = int(_sv_src) if _sv_src.is_integer() else _sv_src")
                lines.append("    else:")
                lines.append("        _sv_txt = str(_sv_src).strip()")
                lines.append("        if not _sv_txt:")
                lines.append("            raise ValueError(f\"set_variables: key '{_sv_key}' has empty number value\")")
                lines.append("        if _sv_txt.isdigit() or (_sv_txt.startswith('-') and _sv_txt[1:].isdigit()):")
                lines.append("            _out[_sv_key] = int(_sv_txt)")
                lines.append("        else:")
                lines.append("            _sv_num = float(_sv_txt)")
                lines.append("            _out[_sv_key] = int(_sv_num) if _sv_num.is_integer() else _sv_num")
                lines.append("elif _sv_type == 'boolean':")
                lines.append("    _sv_m = _TPL_VAR_RE.fullmatch(_sv_raw)")
                lines.append("    if _sv_m:")
                lines.append("        _sv_name = _sv_m.group(1)")
                lines.append("        if _sv_name not in _item:")
                lines.append("            raise ValueError(" + repr(missing_var_msg) + " + _sv_name)")
                lines.append("        _sv_src = _item.get(_sv_name)")
                lines.append("    else:")
                lines.append("        _sv_src = _resolve_template(_sv_raw, _item)")
                lines.append("    if isinstance(_sv_src, bool):")
                lines.append("        _out[_sv_key] = _sv_src")
                lines.append("    elif isinstance(_sv_src, int) and _sv_src in (0, 1):")
                lines.append("        _out[_sv_key] = bool(_sv_src)")
                lines.append("    else:")
                lines.append("        _sv_txt = str(_sv_src).strip().lower()")
                lines.append("        if _sv_txt in ('true', '1'):")
                lines.append("            _out[_sv_key] = True")
                lines.append("        elif _sv_txt in ('false', '0'):")
                lines.append("            _out[_sv_key] = False")
                lines.append("        else:")
                lines.append("            raise ValueError(f\"set_variables: key '{_sv_key}' has invalid boolean value '{_sv_src}'\")")
                lines.append("elif _sv_type == 'array':")
                lines.append("    _sv_m = _TPL_VAR_RE.fullmatch(_sv_raw)")
                lines.append("    if _sv_m:")
                lines.append("        _sv_name = _sv_m.group(1)")
                lines.append("        if _sv_name not in _item:")
                lines.append("            raise ValueError(" + repr(missing_var_msg) + " + _sv_name)")
                lines.append("        _sv_src = _item.get(_sv_name)")
                lines.append("    else:")
                lines.append("        _sv_src = _resolve_template(_sv_raw, _item)")
                lines.append("    if isinstance(_sv_src, list):")
                lines.append("        _out[_sv_key] = list(_sv_src)")
                lines.append("    else:")
                lines.append("        _sv_parsed = json.loads(str(_sv_src))")
                lines.append("        if not isinstance(_sv_parsed, list):")
                lines.append("            raise ValueError(f\"set_variables: key '{_sv_key}' expected JSON array\")")
                lines.append("        _out[_sv_key] = _sv_parsed")
                lines.append("else:")
                lines.append("    _out[_sv_key] = _resolve_template(_sv_raw, _item)")
            code_body = "\n".join(lines)
        
        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop(code_body, indent, include_flag)
