import re

from app.nodes.base import BaseNode


class MapNode(BaseNode):
    NODE_TYPE = "map"

    _EXACT_ITEM_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    _EXACT_GLOBAL_PLACEHOLDER_RE = re.compile(r"^@\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    _EXACT_SECRET_PLACEHOLDER_RE = re.compile(r"^#\{([A-Za-z_][A-Za-z0-9_]*)\}$")

    _INPUT_MODES = ("variable", "secret", "global")
    _VALUE_MODES = ("literal", "variable", "secret", "global")
    _DATA_TYPES = ("string", "number", "boolean")

    _OPERATORS_BY_TYPE = {
        "string": (
            "equals",
            "not_equals",
            "contains",
            "starts_with",
            "ends_with",
            "is_empty",
            "is_not_empty",
        ),
        "number": (
            "equals",
            "not_equals",
            "greater_than",
            "less_than",
            "greater_or_equal",
            "less_or_equal",
        ),
        "boolean": (
            "is_true",
            "is_false",
            "equals",
            "not_equals",
        ),
    }

    _UNARY_OPERATORS = {
        "is_empty",
        "is_not_empty",
        "is_true",
        "is_false",
    }

    @classmethod
    def _normalize_input_mode(cls, raw_mode) -> str:
        value = str(raw_mode or "variable").strip().lower()
        return value if value in cls._INPUT_MODES else "variable"

    @classmethod
    def _normalize_value_mode(cls, raw_mode) -> str:
        value = str(raw_mode or "literal").strip().lower()
        return value if value in cls._VALUE_MODES else "literal"

    @classmethod
    def _normalize_data_type(cls, raw_type) -> str:
        value = str(raw_type or "string").strip().lower()
        return value if value in cls._DATA_TYPES else "string"

    @staticmethod
    def _normalize_operator(raw_operator) -> str:
        return str(raw_operator or "").strip().lower()

    @classmethod
    def _parse_reference_name(cls, raw_value, mode: str) -> str:
        text = str(raw_value or "").strip()
        if not text:
            return ""

        if mode == "variable":
            match = cls._EXACT_ITEM_PLACEHOLDER_RE.fullmatch(text)
            if match:
                return match.group(1)
        elif mode == "secret":
            match = cls._EXACT_SECRET_PLACEHOLDER_RE.fullmatch(text)
            if match:
                return match.group(1)
        elif mode == "global":
            match = cls._EXACT_GLOBAL_PLACEHOLDER_RE.fullmatch(text)
            if match:
                return match.group(1)

        if text.isidentifier():
            return text
        return ""

    @classmethod
    def _extract_rules(cls, config: dict) -> list[dict]:
        raw_rules = config.get("rules")
        if not isinstance(raw_rules, list):
            return []

        rules: list[dict] = []
        for raw in raw_rules:
            item = raw if isinstance(raw, dict) else {}
            rules.append(
                {
                    "operator": cls._normalize_operator(item.get("operator", "")),
                    "compare_raw": "" if item.get("compare_value") is None else str(item.get("compare_value")),
                    "value_mode": cls._normalize_value_mode(item.get("value_mode")),
                    "mapped_value": "" if item.get("mapped_value") is None else str(item.get("mapped_value")),
                }
            )
        return rules

    @classmethod
    def _extract_default(cls, config: dict):
        raw_default = config.get("default")
        if raw_default is None:
            return None
        if not isinstance(raw_default, dict):
            return "__INVALID__"
        return {
            "value_mode": cls._normalize_value_mode(raw_default.get("value_mode")),
            "mapped_value": "" if raw_default.get("mapped_value") is None else str(raw_default.get("mapped_value")),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []

        output_key = str(self.config.get("output_key", "")).strip()
        if not output_key:
            errors.append("map: output_key is required")
        elif not output_key.isidentifier():
            errors.append(f"map: output_key '{output_key}' is not a valid Python identifier")

        raw_input_mode = str(self.config.get("input_value_mode", "variable")).strip().lower()
        input_mode = self._normalize_input_mode(raw_input_mode)
        if raw_input_mode not in self._INPUT_MODES:
            errors.append(f"map: input_value_mode '{raw_input_mode}' is invalid")

        input_source = str(self.config.get("input_source", "")).strip()
        if not input_source:
            errors.append("map: input_source is required")
        elif not self._parse_reference_name(input_source, input_mode):
            errors.append(
                "map: input_source must be a valid local/global/secret reference according to input_value_mode"
            )

        raw_input_type = str(self.config.get("input_data_type", "string")).strip().lower()
        input_type = self._normalize_data_type(raw_input_type)
        if raw_input_type not in self._DATA_TYPES:
            errors.append(f"map: input_data_type '{raw_input_type}' is invalid")

        rules = self._extract_rules(self.config)
        if not rules:
            errors.append("map: rules must be a non-empty list")
        else:
            for idx, rule in enumerate(rules):
                label = f"rule {idx + 1}"
                operator = rule["operator"]
                allowed_ops = self._OPERATORS_BY_TYPE.get(input_type, ())
                if operator not in allowed_ops:
                    errors.append(
                        f"map: {label} operator '{operator}' is not valid for type '{input_type}'"
                    )
                    continue

                compare_raw = str(rule["compare_raw"]).strip()
                if operator not in self._UNARY_OPERATORS and not compare_raw:
                    errors.append(f"map: {label} compare_value is required for operator '{operator}'")

                value_mode = rule["value_mode"]
                if value_mode not in self._VALUE_MODES:
                    errors.append(f"map: {label} value_mode '{value_mode}' is invalid")
                    continue

                mapped_value = str(rule["mapped_value"]).strip()
                if value_mode == "literal":
                    continue

                if not mapped_value:
                    errors.append(f"map: {label} mapped_value is required for value_mode '{value_mode}'")
                    continue

                if not self._parse_reference_name(mapped_value, value_mode):
                    errors.append(
                        f"map: {label} mapped_value must be a valid reference for value_mode '{value_mode}'"
                    )

        default_cfg = self._extract_default(self.config)
        if default_cfg == "__INVALID__":
            errors.append("map: default must be an object when provided")
        elif isinstance(default_cfg, dict):
            default_mode = default_cfg["value_mode"]
            mapped_value = str(default_cfg["mapped_value"]).strip()
            if default_mode not in self._VALUE_MODES:
                errors.append(f"map: default value_mode '{default_mode}' is invalid")
            elif default_mode != "literal":
                if not mapped_value:
                    errors.append(f"map: default mapped_value is required for value_mode '{default_mode}'")
                elif not self._parse_reference_name(mapped_value, default_mode):
                    errors.append(
                        f"map: default mapped_value must be a valid reference for value_mode '{default_mode}'"
                    )

        include_flag = self.config.get("include_other_input_fields", False)
        if not isinstance(include_flag, bool):
            errors.append("map: include_other_input_fields must be a boolean")

        return errors

    def to_code(self, indent: int = 0) -> str:
        output_key = str(self.config.get("output_key", "")).strip()
        input_mode = self._normalize_input_mode(self.config.get("input_value_mode", "variable"))
        input_source = str(self.config.get("input_source", "")).strip()
        input_type = self._normalize_data_type(self.config.get("input_data_type", "string"))
        rules = self._extract_rules(self.config)
        default_cfg = self._extract_default(self.config)
        default_cfg = default_cfg if isinstance(default_cfg, dict) else None

        lines = [
            "# MAP",
            f"_map_output_key = {output_key!r}",
            f"_map_input_mode = {input_mode!r}",
            f"_map_input_source = {input_source!r}",
            f"_map_input_type = {input_type!r}",
            f"_map_rules = {repr(rules)}",
            f"_map_default = {repr(default_cfg)}",
            "_map_unary_ops = {'is_empty', 'is_not_empty', 'is_true', 'is_false'}",
            "",
            "def _map_parse_ref_name(_raw, _mode):",
            "    _txt = str(_raw or '').strip()",
            "    if not _txt:",
            "        return ''",
            "    if _mode == 'variable':",
            "        _m = _TPL_VAR_RE.fullmatch(_txt)",
            "        if _m:",
            "            return _m.group(1)",
            "    elif _mode == 'secret':",
            "        _m = _SECRET_VAR_RE.fullmatch(_txt)",
            "        if _m:",
            "            return _m.group(1)",
            "    elif _mode == 'global':",
            "        _m = _GLOBAL_VAR_RE.fullmatch(_txt)",
            "        if _m:",
            "            return _m.group(1)",
            "    if _txt.isidentifier():",
            "        return _txt",
            "    return ''",
            "",
            "def _map_resolve_ref(_mode, _raw, _field_label):",
            "    _name = _map_parse_ref_name(_raw, _mode)",
            "    if not _name:",
            "        raise ValueError(f\"map: invalid {_field_label} reference '{_raw}' for mode '{_mode}'\")",
            "    if _mode == 'variable':",
            "        if _name not in _item:",
            "            raise ValueError(f\"map: missing variable '{_name}'\")",
            "        return _item.get(_name)",
            "    if _mode == 'secret':",
            "        if _name not in _secret_store:",
            "            raise ValueError(f\"map: missing secret '{_name}'\")",
            "        return _secret_store.get(_name)",
            "    if _mode == 'global':",
            "        if _name not in _global_store:",
            "            raise ValueError(f\"map: missing global variable '{_name}'\")",
            "        return _global_store.get(_name)",
            "    raise ValueError(f\"map: unsupported reference mode '{_mode}'\")",
            "",
            "def _map_resolve_compare(_raw):",
            "    _text = '' if _raw is None else str(_raw)",
            "    _m_local = _TPL_VAR_RE.fullmatch(_text)",
            "    if _m_local:",
            "        _name = _m_local.group(1)",
            "        if _name not in _item:",
            "            raise ValueError(f\"map: missing variable '{_name}' in compare_value\")",
            "        return _item.get(_name)",
            "    _m_secret = _SECRET_VAR_RE.fullmatch(_text)",
            "    if _m_secret:",
            "        _name = _m_secret.group(1)",
            "        if _name not in _secret_store:",
            "            raise ValueError(f\"map: missing secret '{_name}' in compare_value\")",
            "        return _secret_store.get(_name)",
            "    _m_global = _GLOBAL_VAR_RE.fullmatch(_text)",
            "    if _m_global:",
            "        _name = _m_global.group(1)",
            "        if _name not in _global_store:",
            "            raise ValueError(f\"map: missing global variable '{_name}' in compare_value\")",
            "        return _global_store.get(_name)",
            "    if _TPL_VAR_RE.search(_text) or _SECRET_VAR_RE.search(_text) or _GLOBAL_VAR_RE.search(_text):",
            "        return _resolve_template(_text, _item)",
            "    return _raw",
            "",
            "def _map_to_typed(_value, _data_type, _role_label, _operator):",
            "    if _data_type == 'string':",
            "        if _value is None:",
            "            return ''",
            "        return _value if isinstance(_value, str) else str(_value)",
            "",
            "    if _data_type == 'number':",
            "        if isinstance(_value, bool):",
            "            raise ValueError(f\"map: operator '{_operator}' expected number {_role_label}, got boolean\")",
            "        if isinstance(_value, (int, float)):",
            "            return _value",
            "        _txt = str(_value).strip()",
            "        if not _txt:",
            "            raise ValueError(f\"map: operator '{_operator}' expected number {_role_label}, got empty value\")",
            "        try:",
            "            if _txt.isdigit() or (_txt.startswith('-') and _txt[1:].isdigit()):",
            "                return int(_txt)",
            "            return float(_txt)",
            "        except Exception as _num_ex:",
            "            raise ValueError(f\"map: operator '{_operator}' expected number {_role_label}: {_num_ex}\")",
            "",
            "    if _data_type == 'boolean':",
            "        if isinstance(_value, bool):",
            "            return _value",
            "        if isinstance(_value, int) and _value in (0, 1):",
            "            return bool(_value)",
            "        _txt = str(_value).strip().lower()",
            "        if _txt in ('true', '1'):",
            "            return True",
            "        if _txt in ('false', '0'):",
            "            return False",
            "        raise ValueError(f\"map: operator '{_operator}' expected boolean {_role_label}\")",
            "",
            "    raise ValueError(f\"map: unsupported input_data_type '{_data_type}'\")",
            "",
            "def _map_resolve_mapped_value(_mode, _raw):",
            "    if _mode == 'literal':",
            "        return _raw",
            "    return _map_resolve_ref(_mode, _raw, 'mapped_value')",
            "",
            "_map_left = _map_resolve_ref(_map_input_mode, _map_input_source, 'input_source')",
            "_map_matched = False",
            "_map_result = None",
            "for _map_idx, _map_rule in enumerate(_map_rules):",
            "    _map_operator = str(_map_rule.get('operator', '')).strip().lower()",
            "    _map_compare_raw = _map_rule.get('compare_raw', '')",
            "    _map_needs_compare = _map_operator not in _map_unary_ops",
            "    _map_compare = None",
            "    if _map_needs_compare:",
            "        _map_compare = _map_resolve_compare(_map_compare_raw)",
            "",
            "    if _map_input_type == 'string':",
            "        _map_left_typed = _map_to_typed(_map_left, 'string', 'input value', _map_operator)",
            "        if _map_operator == 'is_empty':",
            "            _map_ok = len(_map_left_typed) == 0",
            "        elif _map_operator == 'is_not_empty':",
            "            _map_ok = len(_map_left_typed) > 0",
            "        else:",
            "            _map_right_typed = _map_to_typed(_map_compare, 'string', 'compare_value', _map_operator)",
            "            if _map_operator == 'equals':",
            "                _map_ok = _map_left_typed == _map_right_typed",
            "            elif _map_operator == 'not_equals':",
            "                _map_ok = _map_left_typed != _map_right_typed",
            "            elif _map_operator == 'contains':",
            "                _map_ok = _map_right_typed in _map_left_typed",
            "            elif _map_operator == 'starts_with':",
            "                _map_ok = _map_left_typed.startswith(_map_right_typed)",
            "            elif _map_operator == 'ends_with':",
            "                _map_ok = _map_left_typed.endswith(_map_right_typed)",
            "            else:",
            "                raise ValueError(f\"map: unsupported string operator '{_map_operator}'\")",
            "",
            "    elif _map_input_type == 'number':",
            "        _map_left_typed = _map_to_typed(_map_left, 'number', 'input value', _map_operator)",
            "        _map_right_typed = _map_to_typed(_map_compare, 'number', 'compare_value', _map_operator)",
            "        if _map_operator == 'equals':",
            "            _map_ok = _map_left_typed == _map_right_typed",
            "        elif _map_operator == 'not_equals':",
            "            _map_ok = _map_left_typed != _map_right_typed",
            "        elif _map_operator == 'greater_than':",
            "            _map_ok = _map_left_typed > _map_right_typed",
            "        elif _map_operator == 'less_than':",
            "            _map_ok = _map_left_typed < _map_right_typed",
            "        elif _map_operator == 'greater_or_equal':",
            "            _map_ok = _map_left_typed >= _map_right_typed",
            "        elif _map_operator == 'less_or_equal':",
            "            _map_ok = _map_left_typed <= _map_right_typed",
            "        else:",
            "            raise ValueError(f\"map: unsupported number operator '{_map_operator}'\")",
            "",
            "    elif _map_input_type == 'boolean':",
            "        _map_left_typed = _map_to_typed(_map_left, 'boolean', 'input value', _map_operator)",
            "        if _map_operator == 'is_true':",
            "            _map_ok = _map_left_typed is True",
            "        elif _map_operator == 'is_false':",
            "            _map_ok = _map_left_typed is False",
            "        elif _map_operator in ('equals', 'not_equals'):",
            "            _map_right_typed = _map_to_typed(_map_compare, 'boolean', 'compare_value', _map_operator)",
            "            if _map_operator == 'equals':",
            "                _map_ok = _map_left_typed == _map_right_typed",
            "            else:",
            "                _map_ok = _map_left_typed != _map_right_typed",
            "        else:",
            "            raise ValueError(f\"map: unsupported boolean operator '{_map_operator}'\")",
            "",
            "    else:",
            "        raise ValueError(f\"map: unsupported input_data_type '{_map_input_type}'\")",
            "",
            "    if bool(_map_ok):",
            "        _map_value_mode = str(_map_rule.get('value_mode', 'literal')).strip().lower()",
            "        _map_mapped_raw = _map_rule.get('mapped_value', '')",
            "        _map_result = _map_resolve_mapped_value(_map_value_mode, _map_mapped_raw)",
            "        _map_matched = True",
            "        break",
            "",
            "if not _map_matched:",
            "    if isinstance(_map_default, dict):",
            "        _map_default_mode = str(_map_default.get('value_mode', 'literal')).strip().lower()",
            "        _map_default_raw = _map_default.get('mapped_value', '')",
            "        _map_result = _map_resolve_mapped_value(_map_default_mode, _map_default_raw)",
            "    else:",
            "        raise ValueError('map: no rule matched and no default value is configured')",
            "",
            "_out[_map_output_key] = _map_result",
        ]

        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop("\n".join(lines), indent, include_flag)
