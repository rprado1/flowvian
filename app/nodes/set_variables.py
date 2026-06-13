from app.nodes.base import BaseNode


class SetVariablesNode(BaseNode):
    """
    Sets one or more variables into the workflow context.

    Config:
        variables (list[{key: str, value: str}]): pairs to assign
    """

    NODE_TYPE = "set_variables"

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
                # Store in _out dict instead of scope variable
                lines.append(f"_out[{repr(key)}] = {repr(str(value))}")
            code_body = "\n".join(lines)
        
        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop(code_body, indent, include_flag)
