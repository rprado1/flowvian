from app.nodes.base import BaseNode


class GetCurrentDateUTCNode(BaseNode):
    """
    Captures the current UTC datetime into a context variable.

    Config:
        output_var (str): variable name to store the result — default "current_date_utc"
    """

    NODE_TYPE = "get_current_date_utc"

    def validate(self) -> list[str]:
        errors = []
        output_var = self.config.get("output_var", "current_date_utc").strip()
        if not output_var:
            errors.append("get_current_date_utc: output_var cannot be empty")
        elif not output_var.isidentifier():
            errors.append(f"get_current_date_utc: output_var '{output_var}' is not a valid Python identifier")
        # Accept include_other_input_fields (default False)
        return errors

    def to_code(self, indent: int = 0) -> str:
        output_var = self.config.get("output_var", "current_date_utc").strip() or "current_date_utc"
        lines = [
            "# Get Current Date UTC",
            f"_out[{repr(output_var)}] = datetime.now(timezone.utc).isoformat()",
        ]
        code_body = "\n".join(lines)
        
        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop(code_body, indent, include_flag)
