from __future__ import annotations
import re

from app.nodes.base import BaseNode

VALID_UNITS = ("days", "hours", "minutes", "seconds")


class AddTimeToDateNode(BaseNode):
    """
    Adds a time delta (days, hours, minutes, seconds) to an existing
    datetime variable and stores the result in a new variable.

    Config:
        input_var  (str): name of the source datetime variable
        days       (int|float): days to add (default 0)
        hours      (int|float): hours to add (default 0)
        minutes    (int|float): minutes to add (default 0)
        seconds    (int|float): seconds to add (default 0)
        output_var (str): variable name to store the result (default "new_date")
    """

    NODE_TYPE = "add_time_to_date"
    _PLACEHOLDER_RE = re.compile(r"(?:\$\{[A-Za-z_][A-Za-z0-9_]*\}|@\{[A-Za-z_][A-Za-z0-9_]*\}|#\{[A-Za-z_][A-Za-z0-9_]*\})")

    @classmethod
    def _is_dynamic_value(cls, raw_value) -> bool:
        return isinstance(raw_value, str) and cls._PLACEHOLDER_RE.search(raw_value) is not None

    def validate(self) -> list[str]:
        errors: list[str] = []

        input_var = self.config.get("input_var", "").strip()
        if not input_var:
            errors.append("add_time_to_date: input_var cannot be empty")
        elif not self._is_dynamic_value(input_var) and not input_var.isidentifier():
            errors.append(
                f"add_time_to_date: input_var '{input_var}' must be a variable name or template"
            )

        output_var = self.config.get("output_var", "new_date").strip()
        if not output_var:
            errors.append("add_time_to_date: output_var cannot be empty")
        elif not output_var.isidentifier():
            errors.append(
                f"add_time_to_date: output_var '{output_var}' is not a valid Python identifier"
            )

        for field in VALID_UNITS:
            raw = self.config.get(field, 0)

            if isinstance(raw, bool):
                errors.append(
                    f"add_time_to_date: '{field}' must be a number or variable template, got boolean"
                )
                continue

            if isinstance(raw, (int, float)):
                continue

            text = str(raw).strip()
            if not text:
                errors.append(
                    f"add_time_to_date: '{field}' cannot be empty"
                )
                continue

            if self._is_dynamic_value(text):
                continue

            try:
                float(text)
            except (TypeError, ValueError):
                errors.append(
                    f"add_time_to_date: '{field}' must be a number or variable template, got '{raw}'"
                )

        # Accept include_other_input_fields (default False)
        return errors

    def to_code(self, indent: int = 0) -> str:
        input_var = self.config.get("input_var", "").strip()
        output_var = self.config.get("output_var", "new_date").strip() or "new_date"

        lines = [
            "# Add Time to Date",
            f"_input_var_raw = {input_var!r}",
            "if _TPL_VAR_RE.search(_input_var_raw) or _GLOBAL_VAR_RE.search(_input_var_raw) or _SECRET_VAR_RE.search(_input_var_raw):",
            "    _input_src = _resolve_template(_input_var_raw, _item)",
            "else:",
            "    if _input_var_raw not in _item:",
            "        raise ValueError(f\"add_time_to_date: input variable '{_input_var_raw}' not found\")",
            "    _input_src = _item.get(_input_var_raw)",
            "if isinstance(_input_src, datetime):",
            "    _input_val = _input_src",
            "else:",
            "    _input_val = datetime.fromisoformat(str(_input_src))",
        ]

        for field in VALID_UNITS:
            field_var = f"_atd_{field}"
            raw_value = self.config.get(field, 0)
            lines.extend(
                [
                    f"{field_var}_raw = {raw_value!r}",
                    f"if isinstance({field_var}_raw, bool):",
                    f"    raise ValueError(\"add_time_to_date: '{field}' must be numeric\")",
                    f"if isinstance({field_var}_raw, (int, float)):",
                    f"    {field_var} = float({field_var}_raw)",
                    "else:",
                    f"    {field_var}_txt = str({field_var}_raw).strip()",
                    f"    if not {field_var}_txt:",
                    f"        raise ValueError(\"add_time_to_date: '{field}' cannot be empty\")",
                    f"    if _TPL_VAR_RE.search({field_var}_txt) or _GLOBAL_VAR_RE.search({field_var}_txt) or _SECRET_VAR_RE.search({field_var}_txt):",
                    f"        {field_var}_txt = str(_resolve_template({field_var}_txt, _item)).strip()",
                    "    try:",
                    f"        {field_var} = float({field_var}_txt)",
                    "    except Exception:",
                    f"        raise ValueError(f\"add_time_to_date: '{field}' must resolve to a number, got {{{field_var}_txt!r}}\")",
                    f"if not math.isfinite({field_var}):",
                    f"    raise ValueError(\"add_time_to_date: '{field}' must be finite\")",
                ]
            )

        lines.append(
            f"_out[{repr(output_var)}] = (_input_val + timedelta(days=_atd_days, hours=_atd_hours, minutes=_atd_minutes, seconds=_atd_seconds)).isoformat()"
        )
        code_body = "\n".join(lines)

        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop(code_body, indent, include_flag)
