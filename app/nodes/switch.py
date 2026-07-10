import re

from app.nodes.base import BaseNode


class SwitchNode(BaseNode):
    NODE_TYPE = "switch"

    _EXACT_ITEM_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    _EXACT_GLOBAL_PLACEHOLDER_RE = re.compile(r"^@\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    _EXACT_SECRET_PLACEHOLDER_RE = re.compile(r"^#\{([A-Za-z_][A-Za-z0-9_]*)\}$")
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

    @classmethod
    def _parse_input_reference(cls, text: str) -> tuple[str, str]:
        raw = str(text or "").strip()
        item_match = cls._EXACT_ITEM_PLACEHOLDER_RE.fullmatch(raw)
        if item_match:
            return ("item", item_match.group(1))
        global_match = cls._EXACT_GLOBAL_PLACEHOLDER_RE.fullmatch(raw)
        if global_match:
            return ("global", global_match.group(1))
        secret_match = cls._EXACT_SECRET_PLACEHOLDER_RE.fullmatch(raw)
        if secret_match:
            return ("secret", secret_match.group(1))
        return ("", "")

    @classmethod
    def _normalize_type(cls, raw_type) -> str:
        value = str(raw_type or "string").strip().lower()
        return value if value in cls._TYPES else "string"

    @staticmethod
    def _normalize_operator(raw_operator) -> str:
        return str(raw_operator or "").strip().lower()

    @classmethod
    def _extract_routes(cls, config: dict) -> list[dict]:
        raw_routes = config.get("routes")
        if not isinstance(raw_routes, list) or not raw_routes:
            raw_routes = [
                {
                    "name": "Route 1",
                    "condition": {
                        "input": "${value}",
                        "data_type": "string",
                        "operator": "equals",
                        "compare_value": "",
                    },
                }
            ]

        routes: list[dict] = []
        for idx, raw in enumerate(raw_routes):
            route = raw if isinstance(raw, dict) else {}
            name = str(route.get("name", f"Route {idx + 1}")).strip() or f"Route {idx + 1}"
            raw_cond = route.get("condition")
            cond = raw_cond if isinstance(raw_cond, dict) else {}

            input_expr = str(cond.get("input", "")).strip()
            raw_data_type = str(cond.get("data_type", "string")).strip().lower()
            data_type = cls._normalize_type(raw_data_type)
            operator = cls._normalize_operator(cond.get("operator", ""))
            compare_value = cond.get("compare_value", "")
            compare_raw = "" if compare_value is None else str(compare_value)

            input_scope, input_name = cls._parse_input_reference(input_expr)
            routes.append(
                {
                    "name": name,
                    "output": f"route_{idx + 1}",
                    "input_expr": input_expr,
                    "input_scope": input_scope,
                    "input_name": input_name,
                    "raw_data_type": raw_data_type,
                    "data_type": data_type,
                    "operator": operator,
                    "compare_raw": compare_raw,
                }
            )

        return routes

    def validate(self) -> list[str]:
        errors: list[str] = []
        routes = self._extract_routes(self.config)
        if not routes:
            errors.append("switch: at least one route is required")
            return errors

        discard_unmatched = self.config.get("discard_unmatched", True)
        if not isinstance(discard_unmatched, bool):
            errors.append("switch: discard_unmatched must be a boolean")

        for idx, route in enumerate(routes):
            label = f"route {idx + 1}"
            if not route["name"]:
                errors.append(f"switch: {label} name is required")

            if not route["input_name"]:
                errors.append(
                    f"switch: {label} input must be a variable placeholder like ${{MY_VAR}}, @{{MY_GLOBAL}}, or #{{MY_SECRET}}"
                )

            raw_data_type = route["raw_data_type"]
            data_type = route["data_type"]
            if raw_data_type not in self._TYPES:
                errors.append(f"switch: {label} invalid data_type '{raw_data_type}'")
                continue
            if data_type not in self._TYPES:
                errors.append(f"switch: {label} invalid data_type '{data_type}'")
                continue

            operator = route["operator"]
            allowed_ops = self._OPERATORS_BY_TYPE.get(data_type, ())
            if operator not in allowed_ops:
                errors.append(f"switch: {label} operator '{operator}' is not valid for type '{data_type}'")
                continue

            if operator not in self._UNARY_OPERATORS and str(route["compare_raw"]).strip() == "":
                errors.append(f"switch: {label} compare_value is required for operator '{operator}'")

        return errors

    def to_code(self, indent: int = 0) -> str:
        routes = self._extract_routes(self.config)
        codegen_routes = [
            {
                "name": route["name"],
                "output": route["output"],
                "input_scope": route["input_scope"],
                "input_name": route["input_name"],
                "data_type": route["data_type"],
                "operator": route["operator"],
                "compare_raw": route["compare_raw"],
            }
            for route in routes
        ]

        lines = [
            "# SWITCH",
            f"_switch_routes = {repr(codegen_routes)}",
            "_switch_unary_ops = {'is_true', 'is_false', 'is_empty', 'is_not_empty', 'exists', 'not_exists'}",
            "_branch_outputs = {}",
            "for _switch_cfg in _switch_routes:",
            "    _branch_outputs[str(_switch_cfg.get('output', ''))] = []",
            "_switch_unmatched = []",
            "_switch_route_counts = {str(_switch_cfg.get('output', '')): 0 for _switch_cfg in _switch_routes}",
            "_switch_evaluations = []",
            "for _item in _items:",
            "    _switch_matched_output = None",
            "    _switch_item_checks = []",
            "    for _switch_cfg in _switch_routes:",
            "        _switch_output = str(_switch_cfg.get('output', ''))",
            "        _switch_input_scope = _switch_cfg.get('input_scope', 'item')",
            "        _switch_input_name = _switch_cfg.get('input_name', '')",
            "        _switch_data_type = _switch_cfg.get('data_type', 'string')",
            "        _switch_operator = _switch_cfg.get('operator', '')",
            "        _switch_compare_raw = _switch_cfg.get('compare_raw', '')",
            "",
            "        if _switch_input_scope == 'global':",
            "            if _switch_input_name not in _global_store:",
            "                raise ValueError(f\"switch: missing global variable '{_switch_input_name}'\")",
            "            _switch_left = _global_store.get(_switch_input_name)",
            "        elif _switch_input_scope == 'secret':",
            "            if _switch_input_name not in _secret_store:",
            "                raise ValueError(f\"switch: missing secret '{_switch_input_name}'\")",
            "            _switch_left = _secret_store.get(_switch_input_name)",
            "        else:",
            "            if _switch_input_name not in _item:",
            "                raise ValueError(f\"switch: missing variable '{_switch_input_name}' in input item\")",
            "            _switch_left = _item.get(_switch_input_name)",
            "        _switch_needs_compare = _switch_operator not in _switch_unary_ops",
            "        _switch_right = None",
            "        if _switch_needs_compare:",
            "            _switch_placeholder = _TPL_VAR_RE.fullmatch(_switch_compare_raw)",
            "            if _switch_placeholder:",
            "                _switch_right_name = _switch_placeholder.group(1)",
            "                if _switch_right_name not in _item:",
            "                    raise ValueError(f\"switch: missing variable '{_switch_right_name}' in compare_value\")",
            "                _switch_right = _item.get(_switch_right_name)",
            "            elif _GLOBAL_VAR_RE.fullmatch(_switch_compare_raw):",
            "                _switch_right_name = _GLOBAL_VAR_RE.fullmatch(_switch_compare_raw).group(1)",
            "                if _switch_right_name not in _global_store:",
            "                    raise ValueError(f\"switch: missing global variable '{_switch_right_name}' in compare_value\")",
            "                _switch_right = _global_store.get(_switch_right_name)",
            "            elif _SECRET_VAR_RE.fullmatch(_switch_compare_raw):",
            "                _switch_right_name = _SECRET_VAR_RE.fullmatch(_switch_compare_raw).group(1)",
            "                if _switch_right_name not in _secret_store:",
            "                    raise ValueError(f\"switch: missing secret '{_switch_right_name}' in compare_value\")",
            "                _switch_right = _secret_store.get(_switch_right_name)",
            "            elif _TPL_VAR_RE.search(_switch_compare_raw) or _GLOBAL_VAR_RE.search(_switch_compare_raw) or _SECRET_VAR_RE.search(_switch_compare_raw):",
            "                _switch_right = _resolve_template(_switch_compare_raw, _item)",
            "            else:",
            "                _switch_right = _switch_compare_raw",
            "",
            "        if _switch_data_type == 'string':",
            "            if not isinstance(_switch_left, str):",
            "                raise ValueError(f\"switch: operator '{_switch_operator}' expected string input, got {type(_switch_left).__name__}\")",
            "            if _switch_operator == 'is_empty':",
            "                _switch_result = len(_switch_left) == 0",
            "            elif _switch_operator == 'is_not_empty':",
            "                _switch_result = len(_switch_left) > 0",
            "            else:",
            "                _switch_right_text = str(_switch_right)",
            "                if _switch_operator == 'equals':",
            "                    _switch_result = _switch_left == _switch_right_text",
            "                elif _switch_operator == 'not_equals':",
            "                    _switch_result = _switch_left != _switch_right_text",
            "                elif _switch_operator == 'contains':",
            "                    _switch_result = _switch_right_text in _switch_left",
            "                elif _switch_operator == 'not_contains':",
            "                    _switch_result = _switch_right_text not in _switch_left",
            "                elif _switch_operator == 'starts_with':",
            "                    _switch_result = _switch_left.startswith(_switch_right_text)",
            "                elif _switch_operator == 'ends_with':",
            "                    _switch_result = _switch_left.endswith(_switch_right_text)",
            "                else:",
            "                    raise ValueError(f\"switch: unsupported string operator '{_switch_operator}'\")",
            "",
            "        elif _switch_data_type == 'number':",
            "            def _switch_to_number(_value):",
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
            "                _switch_left_num = _switch_to_number(_switch_left)",
            "            except Exception as _switch_num_ex:",
            "                raise ValueError(f\"switch: operator '{_switch_operator}' expected number input, got {type(_switch_left).__name__}: {_switch_num_ex}\")",
            "",
            "            try:",
            "                _switch_right_num = _switch_to_number(_switch_right)",
            "            except Exception as _switch_num_ex:",
            "                raise ValueError(f\"switch: operator '{_switch_operator}' expected number compare_value, got {type(_switch_right).__name__}: {_switch_num_ex}\")",
            "",
            "            if _switch_operator == 'equals':",
            "                _switch_result = _switch_left_num == _switch_right_num",
            "            elif _switch_operator == 'not_equals':",
            "                _switch_result = _switch_left_num != _switch_right_num",
            "            elif _switch_operator == 'greater_than':",
            "                _switch_result = _switch_left_num > _switch_right_num",
            "            elif _switch_operator == 'less_than':",
            "                _switch_result = _switch_left_num < _switch_right_num",
            "            elif _switch_operator == 'greater_or_equal':",
            "                _switch_result = _switch_left_num >= _switch_right_num",
            "            elif _switch_operator == 'less_or_equal':",
            "                _switch_result = _switch_left_num <= _switch_right_num",
            "            else:",
            "                raise ValueError(f\"switch: unsupported number operator '{_switch_operator}'\")",
            "",
            "        elif _switch_data_type == 'boolean':",
            "            def _switch_to_bool(_value):",
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
            "                _switch_left_bool = _switch_to_bool(_switch_left)",
            "            except Exception as _switch_bool_ex:",
            "                raise ValueError(f\"switch: operator '{_switch_operator}' expected boolean input, got {type(_switch_left).__name__}: {_switch_bool_ex}\")",
            "",
            "            if _switch_operator == 'is_true':",
            "                _switch_result = _switch_left_bool is True",
            "            elif _switch_operator == 'is_false':",
            "                _switch_result = _switch_left_bool is False",
            "            else:",
            "                raise ValueError(f\"switch: unsupported boolean operator '{_switch_operator}'\")",
            "",
            "        elif _switch_data_type == 'object':",
            "            if _switch_left is not None and not isinstance(_switch_left, dict):",
            "                raise ValueError(f\"switch: operator '{_switch_operator}' expected object input, got {type(_switch_left).__name__}\")",
            "            if _switch_operator == 'exists':",
            "                _switch_result = isinstance(_switch_left, dict)",
            "            elif _switch_operator == 'not_exists':",
            "                _switch_result = _switch_left is None",
            "            else:",
            "                if not isinstance(_switch_left, dict):",
            "                    raise ValueError(f\"switch: operator '{_switch_operator}' requires object input, got {type(_switch_left).__name__}\")",
            "                _switch_prop = str(_switch_right)",
            "                if _switch_operator == 'has_property':",
            "                    _switch_result = _switch_prop in _switch_left",
            "                elif _switch_operator == 'not_has_property':",
            "                    _switch_result = _switch_prop not in _switch_left",
            "                else:",
            "                    raise ValueError(f\"switch: unsupported object operator '{_switch_operator}'\")",
            "",
            "        elif _switch_data_type == 'array':",
            "            if not isinstance(_switch_left, list):",
            "                raise ValueError(f\"switch: operator '{_switch_operator}' expected array input, got {type(_switch_left).__name__}\")",
            "            if _switch_operator == 'is_empty':",
            "                _switch_result = len(_switch_left) == 0",
            "            elif _switch_operator == 'is_not_empty':",
            "                _switch_result = len(_switch_left) > 0",
            "            else:",
            "                if isinstance(_switch_right, bool):",
            "                    raise ValueError(f\"switch: operator '{_switch_operator}' expected numeric compare_value, got boolean\")",
            "                try:",
            "                    _switch_len_target = int(float(str(_switch_right).strip()))",
            "                except Exception:",
            "                    raise ValueError(f\"switch: operator '{_switch_operator}' expected numeric compare_value, got {type(_switch_right).__name__}\")",
            "                if _switch_operator == 'length_equals':",
            "                    _switch_result = len(_switch_left) == _switch_len_target",
            "                elif _switch_operator == 'length_greater_than':",
            "                    _switch_result = len(_switch_left) > _switch_len_target",
            "                elif _switch_operator == 'length_less_than':",
            "                    _switch_result = len(_switch_left) < _switch_len_target",
            "                else:",
            "                    raise ValueError(f\"switch: unsupported array operator '{_switch_operator}'\")",
            "",
            "        else:",
            "            raise ValueError(f\"switch: unsupported data_type '{_switch_data_type}'\")",
            "",
            "        _switch_item_checks.append({'output': _switch_output, 'result': bool(_switch_result)})",
            "        if bool(_switch_result):",
            "            _branch_outputs[_switch_output].append(_item)",
            "            _switch_route_counts[_switch_output] = _switch_route_counts.get(_switch_output, 0) + 1",
            "            _switch_matched_output = _switch_output",
            "            break",
            "",
            "    if _switch_matched_output is None:",
            "        _switch_unmatched.append(_item)",
            "",
            "    _switch_evaluations.append({'item_index': len(_switch_evaluations), 'matched_output': _switch_matched_output, 'checks': _switch_item_checks})",
            "",
            "_items = []",
            "for _switch_cfg in _switch_routes:",
            "    _out_name = str(_switch_cfg.get('output', ''))",
            "    _items.extend(list(_branch_outputs.get(_out_name, [])))",
            "",
            "_node_debug = {'switch': {'route_counts': _switch_route_counts, 'matched_items': len(_items), 'unmatched_items': len(_switch_unmatched), 'total_items': len(_items) + len(_switch_unmatched), 'evaluations': _switch_evaluations}}",
        ]

        return self._indent("\n".join(lines), indent)
