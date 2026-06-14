import json

from app.nodes.base import BaseNode


class SetVariablesNode(BaseNode):
    """
    Sets one or more variables into the workflow context.

    Config:
        variables (list[{key: str, value: str}]): pairs to assign
    """

    NODE_TYPE = "set_variables"

    @staticmethod
    def _normalize_type(raw_type) -> str:
        if raw_type is None:
            return "string"
        value = str(raw_type).strip().lower()
        return value or "string"

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
                try:
                    self._parse_number(value)
                except Exception:
                    errors.append(f"set_variables: item {i} value '{value}' is not a valid number")
            elif var_type == "boolean":
                try:
                    self._parse_boolean(value)
                except Exception:
                    errors.append(f"set_variables: item {i} value '{value}' is not a valid boolean")
            elif var_type == "array":
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

                if var_type == "number":
                    parsed_value = self._parse_number(value)
                elif var_type == "boolean":
                    parsed_value = self._parse_boolean(value)
                elif var_type == "array":
                    parsed_value = self._parse_array(value)
                else:
                    parsed_value = str(value)

                # Store in _out dict instead of scope variable
                lines.append(f"_out[{repr(key)}] = {repr(parsed_value)}")
            code_body = "\n".join(lines)
        
        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop(code_body, indent, include_flag)
