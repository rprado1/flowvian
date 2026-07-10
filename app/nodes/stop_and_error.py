from app.nodes.base import BaseNode


class StopAndErrorNode(BaseNode):
    NODE_TYPE = "stop_and_error"

    def validate(self) -> list[str]:
        errors: list[str] = []
        message = self.config.get("message", "")
        if not isinstance(message, str) or not message.strip():
            errors.append("stop_and_error: 'message' is required")
        return errors

    def to_code(self, indent: int = 0) -> str:
        message = str(self.config.get("message", "")).strip()
        lines = [
            "# Stop and Error (stop current execution only)",
            "if not _items:",
            "    pass",
            "else:",
            f"    _stop_message_template = {message!r}",
            "    _stop_item = _items[0]",
            "    try:",
            "        _stop_message = _resolve_template(_stop_message_template, _stop_item)",
            "    except Exception as _stop_msg_ex:",
            "        _stop_message = str(_stop_msg_ex)",
            (
                "    raise _StopIterationExecution(_stop_message, "
                f"node_id={self.node_id!r}, node_type={self.NODE_TYPE!r})"
            ),
        ]
        return self._indent("\n".join(lines), indent)
