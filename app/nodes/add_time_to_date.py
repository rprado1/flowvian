from __future__ import annotations
from typing import Optional
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

    def validate(self) -> list[str]:
        errors: list[str] = []

        input_var = self.config.get("input_var", "").strip()
        if not input_var:
            errors.append("add_time_to_date: input_var cannot be empty")
        elif not input_var.isidentifier():
            errors.append(
                f"add_time_to_date: input_var '{input_var}' is not a valid Python identifier"
            )

        output_var = self.config.get("output_var", "new_date").strip()
        if not output_var:
            errors.append("add_time_to_date: output_var cannot be empty")
        elif not output_var.isidentifier():
            errors.append(
                f"add_time_to_date: output_var '{output_var}' is not a valid Python identifier"
            )

        for field in ("days", "hours", "minutes", "seconds"):
            raw = self.config.get(field, 0)
            try:
                float(raw)
            except (TypeError, ValueError):
                errors.append(
                    f"add_time_to_date: '{field}' must be a number, got '{raw}'"
                )

        return errors

    def to_code(self, indent: int = 0) -> str:
        input_var = self.config.get("input_var", "").strip()
        output_var = self.config.get("output_var", "new_date").strip() or "new_date"

        days = float(self.config.get("days", 0) or 0)
        hours = float(self.config.get("hours", 0) or 0)
        minutes = float(self.config.get("minutes", 0) or 0)
        seconds = float(self.config.get("seconds", 0) or 0)

        # Build timedelta args string — only include non-zero fields for clarity
        args = []
        if days:
            args.append(f"days={days!r}")
        if hours:
            args.append(f"hours={hours!r}")
        if minutes:
            args.append(f"minutes={minutes!r}")
        if seconds:
            args.append(f"seconds={seconds!r}")

        delta_args = ", ".join(args) if args else "seconds=0"

        lines = [
            "# Add Time to Date",
            "from datetime import timedelta",
            f"{output_var} = {input_var} + timedelta({delta_args})",
            f'print(f"Result datetime: {{{output_var}}}")',
        ]
        return self._indent("\n".join(lines), indent)
