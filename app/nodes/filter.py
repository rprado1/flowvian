import re

from app.nodes.base import BaseNode


class FilterNode(BaseNode):
    NODE_TYPE = "filter"

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
            errors.append("filter: at least one condition is required")
            return errors

        for idx, cond in enumerate(conditions):
            label = f"condition {idx + 1}"

            if not cond["input_name"]:
                errors.append(f"filter: {label} input must be a variable placeholder like ${{MY_VAR}}")

            raw_data_type = cond["raw_data_type"]
            data_type = cond["data_type"]
            if raw_data_type not in self._TYPES:
                errors.append(f"filter: {label} invalid data_type '{raw_data_type}'")
                continue
            if data_type not in self._TYPES:
                errors.append(f"filter: {label} invalid data_type '{data_type}'")
                continue

            operator = cond["operator"]
            allowed_ops = self._OPERATORS_BY_TYPE.get(data_type, ())
            if operator not in allowed_ops:
                errors.append(f"filter: {label} operator '{operator}' is not valid for type '{data_type}'")
                continue

            if operator not in self._UNARY_OPERATORS and str(cond["compare_raw"]).strip() == "":
                errors.append(f"filter: {label} compare_value is required for operator '{operator}'")

            if idx > 0 and cond["join"] not in self._LOGIC_OPERATORS:
                errors.append(f"filter: {label} join must be 'and' or 'or'")

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
            "# FILTER",
            f"_filter_conditions = {repr(codegen_conditions)}",
            "_filter_unary_ops = {'is_true', 'is_false', 'is_empty', 'is_not_empty', 'exists', 'not_exists'}",
            "_items_filtered = []",
            "_filter_evaluations = []",
            "for _item in _items:",
            "    if not _filter_conditions:",
            "        raise ValueError('filter: at least one condition is required')",
            "    _filter_item_eval = {'item_index': len(_filter_evaluations), 'conditions': [], 'final_result': False}",
            "    _filter_aggregate = None",
            "    for _filter_idx, _filter_cfg in enumerate(_filter_conditions):",
            "        _filter_input_name = _filter_cfg.get('input_name', '')",
            "        _filter_data_type = _filter_cfg.get('data_type', 'string')",
            "        _filter_operator = _filter_cfg.get('operator', '')",
            "        _filter_compare_raw = _filter_cfg.get('compare_raw', '')",
            "        _filter_join = _filter_cfg.get('join', 'and')",
            "",
            "        if _filter_input_name not in _item:",
            "            raise ValueError(f\"filter: missing variable '{_filter_input_name}' in input item\")",
            "        _filter_left = _item.get(_filter_input_name)",
            "        _filter_left_repr = _filter_left",
            "        _filter_needs_compare = _filter_operator not in _filter_unary_ops",
            "        _filter_right = None",
            "        if _filter_needs_compare:",
            "            _filter_placeholder = _TPL_VAR_RE.fullmatch(_filter_compare_raw)",
            "            if _filter_placeholder:",
            "                _filter_right_name = _filter_placeholder.group(1)",
            "                if _filter_right_name not in _item:",
            "                    raise ValueError(f\"filter: missing variable '{_filter_right_name}' in compare_value\")",
            "                _filter_right = _item.get(_filter_right_name)",
            "            elif _TPL_VAR_RE.search(_filter_compare_raw):",
            "                _filter_right = _resolve_template(_filter_compare_raw, _item)",
            "            else:",
            "                _filter_right = _filter_compare_raw",
            "",
            "        if _filter_data_type == 'string':",
            "            if not isinstance(_filter_left, str):",
            "                raise ValueError(f\"filter: operator '{_filter_operator}' expected string input, got {type(_filter_left).__name__}\")",
            "            if _filter_operator == 'is_empty':",
            "                _filter_result = len(_filter_left) == 0",
            "            elif _filter_operator == 'is_not_empty':",
            "                _filter_result = len(_filter_left) > 0",
            "            else:",
            "                _filter_right_text = str(_filter_right)",
            "                if _filter_operator == 'equals':",
            "                    _filter_result = _filter_left == _filter_right_text",
            "                elif _filter_operator == 'not_equals':",
            "                    _filter_result = _filter_left != _filter_right_text",
            "                elif _filter_operator == 'contains':",
            "                    _filter_result = _filter_right_text in _filter_left",
            "                elif _filter_operator == 'not_contains':",
            "                    _filter_result = _filter_right_text not in _filter_left",
            "                elif _filter_operator == 'starts_with':",
            "                    _filter_result = _filter_left.startswith(_filter_right_text)",
            "                elif _filter_operator == 'ends_with':",
            "                    _filter_result = _filter_left.endswith(_filter_right_text)",
            "                else:",
            "                    raise ValueError(f\"filter: unsupported string operator '{_filter_operator}'\")",
            "",
            "        elif _filter_data_type == 'number':",
            "            def _filter_to_number(_value):",
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
            "                _filter_left_num = _filter_to_number(_filter_left)",
            "            except Exception as _filter_num_ex:",
            "                raise ValueError(f\"filter: operator '{_filter_operator}' expected number input, got {type(_filter_left).__name__}: {_filter_num_ex}\")",
            "",
            "            try:",
            "                _filter_right_num = _filter_to_number(_filter_right)",
            "            except Exception as _filter_num_ex:",
            "                raise ValueError(f\"filter: operator '{_filter_operator}' expected number compare_value, got {type(_filter_right).__name__}: {_filter_num_ex}\")",
            "",
            "            if _filter_operator == 'equals':",
            "                _filter_result = _filter_left_num == _filter_right_num",
            "            elif _filter_operator == 'not_equals':",
            "                _filter_result = _filter_left_num != _filter_right_num",
            "            elif _filter_operator == 'greater_than':",
            "                _filter_result = _filter_left_num > _filter_right_num",
            "            elif _filter_operator == 'less_than':",
            "                _filter_result = _filter_left_num < _filter_right_num",
            "            elif _filter_operator == 'greater_or_equal':",
            "                _filter_result = _filter_left_num >= _filter_right_num",
            "            elif _filter_operator == 'less_or_equal':",
            "                _filter_result = _filter_left_num <= _filter_right_num",
            "            else:",
            "                raise ValueError(f\"filter: unsupported number operator '{_filter_operator}'\")",
            "",
            "        elif _filter_data_type == 'boolean':",
            "            def _filter_to_bool(_value):",
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
            "                _filter_left_bool = _filter_to_bool(_filter_left)",
            "            except Exception as _filter_bool_ex:",
            "                raise ValueError(f\"filter: operator '{_filter_operator}' expected boolean input, got {type(_filter_left).__name__}: {_filter_bool_ex}\")",
            "",
            "            if _filter_operator == 'is_true':",
            "                _filter_result = _filter_left_bool is True",
            "            elif _filter_operator == 'is_false':",
            "                _filter_result = _filter_left_bool is False",
            "            else:",
            "                raise ValueError(f\"filter: unsupported boolean operator '{_filter_operator}'\")",
            "",
            "        elif _filter_data_type == 'object':",
            "            if _filter_left is not None and not isinstance(_filter_left, dict):",
            "                raise ValueError(f\"filter: operator '{_filter_operator}' expected object input, got {type(_filter_left).__name__}\")",
            "            if _filter_operator == 'exists':",
            "                _filter_result = isinstance(_filter_left, dict)",
            "            elif _filter_operator == 'not_exists':",
            "                _filter_result = _filter_left is None",
            "            else:",
            "                if not isinstance(_filter_left, dict):",
            "                    raise ValueError(f\"filter: operator '{_filter_operator}' requires object input, got {type(_filter_left).__name__}\")",
            "                _filter_prop = str(_filter_right)",
            "                if _filter_operator == 'has_property':",
            "                    _filter_result = _filter_prop in _filter_left",
            "                elif _filter_operator == 'not_has_property':",
            "                    _filter_result = _filter_prop not in _filter_left",
            "                else:",
            "                    raise ValueError(f\"filter: unsupported object operator '{_filter_operator}'\")",
            "",
            "        elif _filter_data_type == 'array':",
            "            if not isinstance(_filter_left, list):",
            "                raise ValueError(f\"filter: operator '{_filter_operator}' expected array input, got {type(_filter_left).__name__}\")",
            "            if _filter_operator == 'is_empty':",
            "                _filter_result = len(_filter_left) == 0",
            "            elif _filter_operator == 'is_not_empty':",
            "                _filter_result = len(_filter_left) > 0",
            "            else:",
            "                if isinstance(_filter_right, bool):",
            "                    raise ValueError(f\"filter: operator '{_filter_operator}' expected numeric compare_value, got boolean\")",
            "                try:",
            "                    _filter_len_target = int(float(str(_filter_right).strip()))",
            "                except Exception:",
            "                    raise ValueError(f\"filter: operator '{_filter_operator}' expected numeric compare_value, got {type(_filter_right).__name__}\")",
            "                if _filter_operator == 'length_equals':",
            "                    _filter_result = len(_filter_left) == _filter_len_target",
            "                elif _filter_operator == 'length_greater_than':",
            "                    _filter_result = len(_filter_left) > _filter_len_target",
            "                elif _filter_operator == 'length_less_than':",
            "                    _filter_result = len(_filter_left) < _filter_len_target",
            "                else:",
            "                    raise ValueError(f\"filter: unsupported array operator '{_filter_operator}'\")",
            "",
            "        else:",
            "            raise ValueError(f\"filter: unsupported data_type '{_filter_data_type}'\")",
            "",
            "        if _filter_aggregate is None:",
            "            _filter_aggregate = bool(_filter_result)",
            "        elif _filter_join == 'and':",
            "            _filter_aggregate = _filter_aggregate and bool(_filter_result)",
            "        elif _filter_join == 'or':",
            "            _filter_aggregate = _filter_aggregate or bool(_filter_result)",
            "        else:",
            "            raise ValueError(f\"filter: unsupported join operator '{_filter_join}'\")",
            "",
            "        _filter_item_eval['conditions'].append({",
            "            'variable': '${' + _filter_input_name + '}',",
            "            'resolved_value': _filter_left_repr,",
            "            'operator': _filter_operator,",
            "            'compare_value': _filter_compare_raw if _filter_needs_compare else None,",
            "            'resolved_compare': _filter_right if _filter_needs_compare else None,",
            "            'join': None if _filter_idx == 0 else _filter_join.upper(),",
            "            'result': bool(_filter_result),",
            "        })",
            "",
            "    _filter_item_eval['final_result'] = bool(_filter_aggregate)",
            "    _filter_evaluations.append(_filter_item_eval)",
            "",
            "    if bool(_filter_aggregate):",
            "        _items_filtered.append(_item)",
            "",
            "_node_debug = {'filter_evaluations': _filter_evaluations, 'counts': {'items_in': len(_items), 'items_out': len(_items_filtered), 'filtered_out': len(_items) - len(_items_filtered)}}",
            "_items = _items_filtered",
            "_branch_outputs = {'output_1': _items_filtered}",
        ]

        return self._indent("\n".join(lines), indent)
