import re

from app.nodes.base import BaseNode


class IfNode(BaseNode):
    NODE_TYPE = "if"

    _EXACT_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    _TYPES = ("string", "number", "boolean", "object", "array")
    _OPERATORS_BY_TYPE = {
        "string": (
            "equals",
            "not_equals",
            "contains",
            "not_contains",
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
        ),
        "object": (
            "exists",
            "not_exists",
            "has_property",
            "not_has_property",
        ),
        "array": (
            "is_empty",
            "is_not_empty",
            "length_equals",
            "length_greater_than",
            "length_less_than",
        ),
    }
    _UNARY_OPERATORS = {
        "is_true",
        "is_false",
        "is_empty",
        "is_not_empty",
        "exists",
        "not_exists",
    }
    _LOGIC_OPERATORS = {"and", "or"}

    @classmethod
    def _normalize_type(cls, raw_type) -> str:
        value = str(raw_type or "string").strip().lower()
        return value if value in cls._TYPES else "string"

    @staticmethod
    def _normalize_operator(raw_operator) -> str:
        return str(raw_operator or "").strip().lower()

    @classmethod
    def _normalize_join(cls, raw_join) -> str:
        join = str(raw_join or "and").strip().lower()
        return join if join in cls._LOGIC_OPERATORS else "and"

    @classmethod
    def _parse_placeholder_name(cls, text: str) -> str:
        match = cls._EXACT_PLACEHOLDER_RE.fullmatch(str(text or "").strip())
        if not match:
            return ""
        return match.group(1)

    @classmethod
    def _extract_conditions(cls, config: dict) -> list[dict]:
        raw_conditions = config.get("conditions")
        if isinstance(raw_conditions, list) and raw_conditions:
            source = raw_conditions
        else:
            source = [
                {
                    "input": config.get("input", ""),
                    "data_type": config.get("data_type", "string"),
                    "operator": config.get("operator", ""),
                    "compare_value": config.get("compare_value", ""),
                    "join": "and",
                }
            ]

        conditions: list[dict] = []
        for idx, raw in enumerate(source):
            item = raw if isinstance(raw, dict) else {}
            input_expr = str(item.get("input", "")).strip()
            raw_data_type = str(item.get("data_type", "string")).strip().lower()
            data_type = cls._normalize_type(raw_data_type)
            operator = cls._normalize_operator(item.get("operator", ""))
            compare_value = item.get("compare_value", "")
            compare_raw = "" if compare_value is None else str(compare_value)
            join = "and" if idx == 0 else cls._normalize_join(item.get("join", "and"))

            conditions.append(
                {
                    "input_expr": input_expr,
                    "input_name": cls._parse_placeholder_name(input_expr),
                    "raw_data_type": raw_data_type,
                    "data_type": data_type,
                    "operator": operator,
                    "compare_raw": compare_raw,
                    "join": join,
                }
            )

        return conditions

    def validate(self) -> list[str]:
        errors: list[str] = []

        conditions = self._extract_conditions(self.config)
        if not conditions:
            errors.append("if: at least one condition is required")
            return errors

        for idx, cond in enumerate(conditions):
            label = f"condition {idx + 1}"

            if not cond["input_name"]:
                errors.append(f"if: {label} input must be a variable placeholder like ${{MY_VAR}}")

            raw_data_type = cond["raw_data_type"]
            data_type = cond["data_type"]
            if raw_data_type not in self._TYPES:
                errors.append(f"if: {label} invalid data_type '{raw_data_type}'")
                continue
            if data_type not in self._TYPES:
                errors.append(f"if: {label} invalid data_type '{data_type}'")
                continue

            operator = cond["operator"]
            allowed_ops = self._OPERATORS_BY_TYPE.get(data_type, ())
            if operator not in allowed_ops:
                errors.append(f"if: {label} operator '{operator}' is not valid for type '{data_type}'")
                continue

            if operator not in self._UNARY_OPERATORS and str(cond["compare_raw"]).strip() == "":
                errors.append(f"if: {label} compare_value is required for operator '{operator}'")

            if idx > 0 and cond["join"] not in self._LOGIC_OPERATORS:
                errors.append(f"if: {label} join must be 'and' or 'or'")

        return errors

    def to_code(self, indent: int = 0) -> str:
        conditions = self._extract_conditions(self.config)
        codegen_conditions = [
            {
                "input_name": cond["input_name"],
                "data_type": cond["data_type"],
                "operator": cond["operator"],
                "compare_raw": cond["compare_raw"],
                "join": cond["join"],
            }
            for cond in conditions
        ]

        lines = [
            "# IF",
            f"_if_conditions = {repr(codegen_conditions)}",
            "_if_unary_ops = {'is_true', 'is_false', 'is_empty', 'is_not_empty', 'exists', 'not_exists'}",
            "_items_true = []",
            "_items_false = []",
            "for _item in _items:",
            "    if not _if_conditions:",
            "        raise ValueError('if: at least one condition is required')",
            "    _if_aggregate = None",
            "    for _if_idx, _if_cfg in enumerate(_if_conditions):",
            "        _if_input_name = _if_cfg.get('input_name', '')",
            "        _if_data_type = _if_cfg.get('data_type', 'string')",
            "        _if_operator = _if_cfg.get('operator', '')",
            "        _if_compare_raw = _if_cfg.get('compare_raw', '')",
            "        _if_join = _if_cfg.get('join', 'and')",
            "",
            "        if _if_input_name not in _item:",
            "            raise ValueError(f\"if: missing variable '{_if_input_name}' in input item\")",
            "        _if_left = _item.get(_if_input_name)",
            "        _if_needs_compare = _if_operator not in _if_unary_ops",
            "        _if_right = None",
            "        if _if_needs_compare:",
            "            _if_placeholder = _TPL_VAR_RE.fullmatch(_if_compare_raw)",
            "            if _if_placeholder:",
            "                _if_right_name = _if_placeholder.group(1)",
            "                if _if_right_name not in _item:",
            "                    raise ValueError(f\"if: missing variable '{_if_right_name}' in compare_value\")",
            "                _if_right = _item.get(_if_right_name)",
            "            elif _TPL_VAR_RE.search(_if_compare_raw):",
            "                _if_right = _resolve_template(_if_compare_raw, _item)",
            "            else:",
            "                _if_right = _if_compare_raw",
            "",
            "        if _if_data_type == 'string':",
            "            if not isinstance(_if_left, str):",
            "                raise ValueError(f\"if: operator '{_if_operator}' expected string input, got {type(_if_left).__name__}\")",
            "            if _if_operator == 'is_empty':",
            "                _if_result = len(_if_left) == 0",
            "            elif _if_operator == 'is_not_empty':",
            "                _if_result = len(_if_left) > 0",
            "            else:",
            "                _if_right_text = str(_if_right)",
            "                if _if_operator == 'equals':",
            "                    _if_result = _if_left == _if_right_text",
            "                elif _if_operator == 'not_equals':",
            "                    _if_result = _if_left != _if_right_text",
            "                elif _if_operator == 'contains':",
            "                    _if_result = _if_right_text in _if_left",
            "                elif _if_operator == 'not_contains':",
            "                    _if_result = _if_right_text not in _if_left",
            "                elif _if_operator == 'starts_with':",
            "                    _if_result = _if_left.startswith(_if_right_text)",
            "                elif _if_operator == 'ends_with':",
            "                    _if_result = _if_left.endswith(_if_right_text)",
            "                else:",
            "                    raise ValueError(f\"if: unsupported string operator '{_if_operator}'\")",
            "",
            "        elif _if_data_type == 'number':",
            "            def _if_to_number(_value):",
            "                if isinstance(_value, bool):",
            "                    raise ValueError('boolean is not a number')",
            "                if isinstance(_value, int):",
            "                    return _value",
            "                if isinstance(_value, float):",
            "                    return _value",
            "                _txt = str(_value).strip()",
            "                if not _txt:",
            "                    raise ValueError('empty number value')",
            "                return float(_txt)",
            "",
            "            try:",
            "                _if_left_num = _if_to_number(_if_left)",
            "            except Exception as _if_num_ex:",
            "                raise ValueError(f\"if: operator '{_if_operator}' expected number input, got {type(_if_left).__name__}: {_if_num_ex}\")",
            "",
            "            try:",
            "                _if_right_num = _if_to_number(_if_right)",
            "            except Exception as _if_num_ex:",
            "                raise ValueError(f\"if: operator '{_if_operator}' expected number compare_value, got {type(_if_right).__name__}: {_if_num_ex}\")",
            "",
            "            if _if_operator == 'equals':",
            "                _if_result = _if_left_num == _if_right_num",
            "            elif _if_operator == 'not_equals':",
            "                _if_result = _if_left_num != _if_right_num",
            "            elif _if_operator == 'greater_than':",
            "                _if_result = _if_left_num > _if_right_num",
            "            elif _if_operator == 'less_than':",
            "                _if_result = _if_left_num < _if_right_num",
            "            elif _if_operator == 'greater_or_equal':",
            "                _if_result = _if_left_num >= _if_right_num",
            "            elif _if_operator == 'less_or_equal':",
            "                _if_result = _if_left_num <= _if_right_num",
            "            else:",
            "                raise ValueError(f\"if: unsupported number operator '{_if_operator}'\")",
            "",
            "        elif _if_data_type == 'boolean':",
            "            def _if_to_bool(_value):",
            "                if isinstance(_value, bool):",
            "                    return _value",
            "                if isinstance(_value, int) and _value in (0, 1):",
            "                    return bool(_value)",
            "                _txt = str(_value).strip().lower()",
            "                if _txt in ('true', '1'):",
            "                    return True",
            "                if _txt in ('false', '0'):",
            "                    return False",
            "                raise ValueError('invalid boolean value')",
            "",
            "            try:",
            "                _if_left_bool = _if_to_bool(_if_left)",
            "            except Exception as _if_bool_ex:",
            "                raise ValueError(f\"if: operator '{_if_operator}' expected boolean input, got {type(_if_left).__name__}: {_if_bool_ex}\")",
            "",
            "            if _if_operator == 'is_true':",
            "                _if_result = _if_left_bool is True",
            "            elif _if_operator == 'is_false':",
            "                _if_result = _if_left_bool is False",
            "            else:",
            "                raise ValueError(f\"if: unsupported boolean operator '{_if_operator}'\")",
            "",
            "        elif _if_data_type == 'object':",
            "            if _if_left is not None and not isinstance(_if_left, dict):",
            "                raise ValueError(f\"if: operator '{_if_operator}' expected object input, got {type(_if_left).__name__}\")",
            "            if _if_operator == 'exists':",
            "                _if_result = isinstance(_if_left, dict)",
            "            elif _if_operator == 'not_exists':",
            "                _if_result = _if_left is None",
            "            else:",
            "                if not isinstance(_if_left, dict):",
            "                    raise ValueError(f\"if: operator '{_if_operator}' requires object input, got {type(_if_left).__name__}\")",
            "                _if_prop = str(_if_right)",
            "                if _if_operator == 'has_property':",
            "                    _if_result = _if_prop in _if_left",
            "                elif _if_operator == 'not_has_property':",
            "                    _if_result = _if_prop not in _if_left",
            "                else:",
            "                    raise ValueError(f\"if: unsupported object operator '{_if_operator}'\")",
            "",
            "        elif _if_data_type == 'array':",
            "            if not isinstance(_if_left, list):",
            "                raise ValueError(f\"if: operator '{_if_operator}' expected array input, got {type(_if_left).__name__}\")",
            "            if _if_operator == 'is_empty':",
            "                _if_result = len(_if_left) == 0",
            "            elif _if_operator == 'is_not_empty':",
            "                _if_result = len(_if_left) > 0",
            "            else:",
            "                if isinstance(_if_right, bool):",
            "                    raise ValueError(f\"if: operator '{_if_operator}' expected numeric compare_value, got boolean\")",
            "                try:",
            "                    _if_len_target = int(float(str(_if_right).strip()))",
            "                except Exception:",
            "                    raise ValueError(f\"if: operator '{_if_operator}' expected numeric compare_value, got {type(_if_right).__name__}\")",
            "                if _if_operator == 'length_equals':",
            "                    _if_result = len(_if_left) == _if_len_target",
            "                elif _if_operator == 'length_greater_than':",
            "                    _if_result = len(_if_left) > _if_len_target",
            "                elif _if_operator == 'length_less_than':",
            "                    _if_result = len(_if_left) < _if_len_target",
            "                else:",
            "                    raise ValueError(f\"if: unsupported array operator '{_if_operator}'\")",
            "",
            "        else:",
            "            raise ValueError(f\"if: unsupported data_type '{_if_data_type}'\")",
            "",
            "        if _if_aggregate is None:",
            "            _if_aggregate = bool(_if_result)",
            "        elif _if_join == 'and':",
            "            _if_aggregate = _if_aggregate and bool(_if_result)",
            "        elif _if_join == 'or':",
            "            _if_aggregate = _if_aggregate or bool(_if_result)",
            "        else:",
            "            raise ValueError(f\"if: unsupported join operator '{_if_join}'\")",
            "",
            "    if bool(_if_aggregate):",
            "        _items_true.append(_item)",
            "    else:",
            "        _items_false.append(_item)",
            "",
            "_branch_outputs = {'true': _items_true, 'false': _items_false}",
            "_items = _items_true + _items_false",
        ]

        return self._indent("\n".join(lines), indent)
