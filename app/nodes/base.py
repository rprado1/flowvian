from abc import ABC, abstractmethod


class BaseNode(ABC):
    """
    Abstract base for all workflow nodes.

    Each node must be able to:
    - validate its config
    - generate Python source code for the compiled workflow
    """

    # Override in subclasses with the node type identifier
    NODE_TYPE: str = ""

    def __init__(self, node_id: str, config: dict):
        self.node_id = node_id
        self.config = config

    @abstractmethod
    def validate(self) -> list[str]:
        """
        Validate the node config.
        Returns a list of error strings (empty = valid).
        """

    @abstractmethod
    def to_code(self, indent: int = 0) -> str:
        """
        Generate Python source code for this node's logic.
        'indent' is the number of spaces for indentation.
        """

    def _indent(self, code: str, spaces: int) -> str:
        prefix = " " * spaces
        return "\n".join(prefix + line for line in code.splitlines())

    def _emit_item_loop(self, code_body: str, indent: int, include_flag: bool) -> str:
        """
        Wraps node code in a for-loop over _items.
        Each iteration processes one item, produces _out dict.
        If include_flag is True, _out inherits all fields from _item.
        """
        lines = [
            "_items_out = []",
            "for _item in _items:",
            "    _out = {}",
        ]
        # Indent the code_body by 4 spaces (inside the for loop)
        for line in code_body.splitlines():
            lines.append("    " + line)
        
        if include_flag:
            lines.append("    _out = {**_item, **_out}")
        lines.append("    _items_out.append(_out)")
        lines.append("_items = _items_out")
        
        return self._indent("\n".join(lines), indent)

    @property
    def var_name(self) -> str:
        """Safe Python variable name derived from node id."""
        return f"node_{self.node_id}"
