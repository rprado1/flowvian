from app.nodes.base import BaseNode

VALID_UNITS = ("seconds", "minutes", "hours")


class SchedulerNode(BaseNode):
    """
    Wraps the rest of the workflow in a while-True loop with time.sleep.

    Config:
        interval (int|float): how often to run — default 60
        unit     (str):       "seconds" | "minutes" | "hours" — default "seconds"
    """

    NODE_TYPE = "scheduler"

    def validate(self) -> list[str]:
        errors = []
        interval = self.config.get("interval")
        try:
            v = float(interval)
            if v <= 0:
                errors.append("Scheduler interval must be greater than 0")
        except (TypeError, ValueError):
            errors.append("Scheduler interval must be a positive number")

        unit = self.config.get("unit", "seconds")
        if unit not in VALID_UNITS:
            errors.append(f"Scheduler unit must be one of: {', '.join(VALID_UNITS)}")

        return errors

    def to_code(self, indent: int = 0) -> str:
        interval = float(self.config.get("interval", 60))
        unit = self.config.get("unit", "seconds")

        multipliers = {"seconds": 1, "minutes": 60, "hours": 3600}
        sleep_seconds = interval * multipliers[unit]

        lines = [
            f"# Scheduler: every {interval} {unit}",
            f"_sleep_seconds = {sleep_seconds}",
            "while True:",
        ]
        return self._indent("\n".join(lines), indent)

    def loop_close_code(self, indent: int = 0) -> str:
        """Code that closes the while-True loop (time.sleep call)."""
        lines = [
            "    import time",
            "    time.sleep(_sleep_seconds)",
        ]
        return self._indent("\n".join(lines), indent)
