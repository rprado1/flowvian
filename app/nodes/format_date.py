import re

from app.nodes.base import BaseNode


class FormatDateNode(BaseNode):
    NODE_TYPE = "format_date"

    _EXACT_ITEM_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    _EXACT_GLOBAL_PLACEHOLDER_RE = re.compile(r"^@\{([A-Za-z_][A-Za-z0-9_]*)\}$")
    _ALLOWED_FORMATS = {
        "iso_8601",
        "date_yyyy_mm_dd",
        "datetime_yyyy_mm_dd_hh_mm_ss",
        "time_hh_mm_ss",
        "unix_timestamp",
        "unix_ms_timestamp",
    }

    @classmethod
    def _parse_input_reference(cls, raw_input) -> tuple[str, str]:
        text = str(raw_input or "").strip()
        item_match = cls._EXACT_ITEM_PLACEHOLDER_RE.fullmatch(text)
        if item_match:
            return ("item", item_match.group(1))
        global_match = cls._EXACT_GLOBAL_PLACEHOLDER_RE.fullmatch(text)
        if global_match:
            return ("global", global_match.group(1))
        return ("", "")

    def validate(self) -> list[str]:
        errors: list[str] = []

        input_scope, input_name = self._parse_input_reference(self.config.get("input", ""))
        if not input_name:
            errors.append("format_date: input must be a variable placeholder like ${MY_DATE} or @{MY_GLOBAL_DATE}")

        format_name = str(self.config.get("format", "iso_8601")).strip()
        if format_name not in self._ALLOWED_FORMATS:
            errors.append(f"format_date: unsupported format '{format_name}'")

        output_var = str(self.config.get("output_var", "formatted_date")).strip()
        if not output_var:
            errors.append("format_date: output_var cannot be empty")
        elif not output_var.isidentifier():
            errors.append(f"format_date: output_var '{output_var}' is not a valid Python identifier")

        include_flag = self.config.get("include_other_input_fields", False)
        if not isinstance(include_flag, bool):
            errors.append("format_date: include_other_input_fields must be a boolean")

        return errors

    def to_code(self, indent: int = 0) -> str:
        input_scope, input_name = self._parse_input_reference(self.config.get("input", ""))
        format_name = str(self.config.get("format", "iso_8601")).strip() or "iso_8601"
        output_var = str(self.config.get("output_var", "formatted_date")).strip() or "formatted_date"

        lines = [
            "# Format Date",
            f"_fd_input_scope = {input_scope!r}",
            f"_fd_input_name = {input_name!r}",
            f"_fd_format = {format_name!r}",
            f"_fd_output_var = {output_var!r}",
            "if _fd_input_scope == 'global':",
            "    if _fd_input_name not in _global_store:",
            "        raise ValueError(f\"format_date: missing global variable '{_fd_input_name}'\")",
            "    _fd_raw = _global_store.get(_fd_input_name)",
            "else:",
            "    if _fd_input_name not in _item:",
            "        raise ValueError(f\"format_date: missing variable '{_fd_input_name}' in input item\")",
            "    _fd_raw = _item.get(_fd_input_name)",
            "_fd_dt = None",
            "if isinstance(_fd_raw, datetime):",
            "    _fd_dt = _fd_raw",
            "elif isinstance(_fd_raw, bool):",
            "    raise ValueError(f\"format_date: cannot parse input date for variable '{_fd_input_name}'\")",
            "elif isinstance(_fd_raw, (int, float)):",
            "    _fd_num = float(_fd_raw)",
            "    if abs(_fd_num) >= 1_000_000_000_000:",
            "        _fd_dt = datetime.fromtimestamp(_fd_num / 1000.0, tz=timezone.utc)",
            "    else:",
            "        _fd_dt = datetime.fromtimestamp(_fd_num, tz=timezone.utc)",
            "elif isinstance(_fd_raw, str):",
            "    _fd_txt = _fd_raw.strip()",
            "    if not _fd_txt:",
            "        raise ValueError(f\"format_date: cannot parse input date for variable '{_fd_input_name}'\")",
            "    _fd_iso_txt = _fd_txt[:-1] + '+00:00' if _fd_txt.endswith('Z') else _fd_txt",
            "    try:",
            "        _fd_dt = datetime.fromisoformat(_fd_iso_txt)",
            "    except Exception:",
            "        try:",
            "            _fd_num = float(_fd_txt)",
            "            if abs(_fd_num) >= 1_000_000_000_000:",
            "                _fd_dt = datetime.fromtimestamp(_fd_num / 1000.0, tz=timezone.utc)",
            "            else:",
            "                _fd_dt = datetime.fromtimestamp(_fd_num, tz=timezone.utc)",
            "        except Exception:",
            "            raise ValueError(f\"format_date: cannot parse input date for variable '{_fd_input_name}'\")",
            "else:",
            "    raise ValueError(f\"format_date: cannot parse input date for variable '{_fd_input_name}'\")",
            "",
            "if _fd_dt.tzinfo is None:",
            "    _fd_dt = _fd_dt.replace(tzinfo=timezone.utc)",
            "_fd_dt_utc = _fd_dt.astimezone(timezone.utc)",
            "",
            "if _fd_format == 'iso_8601':",
            "    _fd_formatted = _fd_dt_utc.isoformat().replace('+00:00', 'Z')",
            "elif _fd_format == 'date_yyyy_mm_dd':",
            "    _fd_formatted = _fd_dt_utc.strftime('%Y-%m-%d')",
            "elif _fd_format == 'datetime_yyyy_mm_dd_hh_mm_ss':",
            "    _fd_formatted = _fd_dt_utc.strftime('%Y-%m-%d %H:%M:%S')",
            "elif _fd_format == 'time_hh_mm_ss':",
            "    _fd_formatted = _fd_dt_utc.strftime('%H:%M:%S')",
            "elif _fd_format == 'unix_timestamp':",
            "    _fd_formatted = int(_fd_dt_utc.timestamp())",
            "elif _fd_format == 'unix_ms_timestamp':",
            "    _fd_formatted = int(_fd_dt_utc.timestamp() * 1000)",
            "else:",
            "    raise ValueError(f\"format_date: unsupported format '{_fd_format}'\")",
            "",
            "_out[_fd_output_var] = _fd_formatted",
        ]

        include_flag = self.config.get("include_other_input_fields", False)
        return self._emit_item_loop("\n".join(lines), indent, include_flag)
