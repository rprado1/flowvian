from app.nodes.base import BaseNode


class WaitNode(BaseNode):
    NODE_TYPE = "wait"

    def validate(self) -> list[str]:
        errors: list[str] = []
        raw_seconds = self.config.get("seconds", 1)
        try:
            seconds = float(raw_seconds)
            if seconds < 0:
                errors.append("wait: seconds must be greater than or equal to 0")
        except (TypeError, ValueError):
            errors.append("wait: seconds must be a number")
        return errors

    def to_code(self, indent: int = 0) -> str:
        seconds = float(self.config.get("seconds", 1) or 0)
        lines = [
            "# Wait",
            f"time.sleep({seconds!r})",
        ]
        return self._indent("\n".join(lines), indent)
