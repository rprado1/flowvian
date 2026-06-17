"""
Code Generator
==============
Takes a workflow graph (nodes + edges) and produces a standalone Python script
that can be compiled to an .exe with PyInstaller.

Execution order is determined via topological sort of the DAG formed by edges.
Nodes at the same topological level (independent branches) are executed in
parallel using concurrent.futures.ThreadPoolExecutor.
If a Scheduler node is present it wraps all subsequent nodes in a while-True loop.
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Optional, cast
from app.nodes.base import BaseNode
from app.nodes.scheduler import SchedulerNode
from app.nodes.set_variables import SetVariablesNode
from app.nodes.get_current_date import GetCurrentDateUTCNode
from app.nodes.add_time_to_date import AddTimeToDateNode
from app.nodes.merge import MergeNode
from app.nodes.subtract_time_from_date import SubtractTimeFromDateNode
from app.nodes.wait import WaitNode
from app.nodes.http_request import HttpRequestNode
from app.nodes.if_node import IfNode
from app.nodes.filter import FilterNode
from app.nodes.stop_and_error import StopAndErrorNode
from app.nodes.split import SplitNode
from app.nodes.aggregate import AggregateNode
from app.nodes.format_date import FormatDateNode
from app.nodes.sort import SortNode
from app.nodes.switch import SwitchNode


NODE_REGISTRY: dict[str, type[BaseNode]] = {
    SchedulerNode.NODE_TYPE: SchedulerNode,
    SetVariablesNode.NODE_TYPE: SetVariablesNode,
    GetCurrentDateUTCNode.NODE_TYPE: GetCurrentDateUTCNode,
    AddTimeToDateNode.NODE_TYPE: AddTimeToDateNode,
    MergeNode.NODE_TYPE: MergeNode,
    SubtractTimeFromDateNode.NODE_TYPE: SubtractTimeFromDateNode,
    WaitNode.NODE_TYPE: WaitNode,
    HttpRequestNode.NODE_TYPE: HttpRequestNode,
    IfNode.NODE_TYPE: IfNode,
    FilterNode.NODE_TYPE: FilterNode,
    StopAndErrorNode.NODE_TYPE: StopAndErrorNode,
    SplitNode.NODE_TYPE: SplitNode,
    AggregateNode.NODE_TYPE: AggregateNode,
    FormatDateNode.NODE_TYPE: FormatDateNode,
    SortNode.NODE_TYPE: SortNode,
    SwitchNode.NODE_TYPE: SwitchNode,
}

SCRIPT_HEADER = '''\
# ============================================================
# Auto-generated workflow script
# DO NOT EDIT MANUALLY
# ============================================================
import sys
import os
import json
import logging
import traceback
import uuid
import re
import base64
import hashlib
import hmac
import socket
import ipaddress
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor as _TPE, wait as _wait, ALL_COMPLETED as _ALL
from urllib.parse import urlparse
from urllib.parse import urlencode as _urlencode
from urllib.request import Request as _UrlRequest, urlopen as _urlopen
from urllib.error import HTTPError as _HTTPError, URLError as _URLError

# ---- Error log setup ----
# Log file is placed next to the .exe (or .py when running from source)
_exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))
_log_path = os.path.join(_exe_dir, WORKFLOW_NAME.replace(" ", "_") + "_errors.log")
logging.basicConfig(
    filename=_log_path,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger(__name__)

_TPL_VAR_RE = re.compile(r"\\$\\{([A-Za-z_][A-Za-z0-9_]*)\\}")
_SECRET_VAR_RE = re.compile(r"#\\{([A-Za-z_][A-Za-z0-9_]*)\\}")
_MAX_REQUEST_BODY_BYTES = 1_000_000
_MAX_RESPONSE_BODY_BYTES = 2_000_000
_SECRET_PREFIX = "enc:v1:"
_secret_store = {}

def _load_master_key():
    _raw = os.environ.get("W_METADATA_1", "").strip()
    if not _raw:
        raise ValueError("Missing required environment variable: W_METADATA_1")
    return _raw.encode("utf-8")

def _derive_stream_key(_master_key, _salt):
    return hashlib.pbkdf2_hmac("sha256", _master_key, _salt, 120000, dklen=32)

def _xor_bytes(_data, _stream):
    _out = bytearray(len(_data))
    _stream_len = len(_stream)
    for _idx, _byte in enumerate(_data):
        _out[_idx] = _byte ^ _stream[_idx % _stream_len]
    return bytes(_out)

def _decrypt_secret_value(_ciphertext):
    if not isinstance(_ciphertext, str) or not _ciphertext.startswith(_SECRET_PREFIX):
        raise ValueError("Invalid encrypted secret format")
    _payload_b64 = _ciphertext[len(_SECRET_PREFIX):]
    try:
        _payload = base64.urlsafe_b64decode(_payload_b64.encode("ascii"))
    except Exception as _ex:
        raise ValueError("Invalid encrypted secret payload") from _ex
    if len(_payload) < 48:
        raise ValueError("Encrypted secret payload is too short")

    _salt = _payload[:16]
    _mac = _payload[16:48]
    _cipher_bytes = _payload[48:]
    _master_key = _load_master_key()
    _expected_mac = hmac.new(_master_key, _salt + _cipher_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(_mac, _expected_mac):
        raise ValueError("Secret integrity check failed")

    _stream = _derive_stream_key(_master_key, _salt)
    _plain = _xor_bytes(_cipher_bytes, _stream)
    try:
        return _plain.decode("utf-8")
    except Exception as _ex:
        raise ValueError("Decrypted secret is not valid UTF-8") from _ex

def _resolve_secret_placeholders(_text):
    if not isinstance(_text, str):
        return _text

    def _replace(_match):
        _name = _match.group(1)
        if _name not in _secret_store:
            raise ValueError(f"Missing secret: {_name}")
        _value = _secret_store.get(_name)
        if _value is None:
            return ""
        return str(_value)

    return _SECRET_VAR_RE.sub(_replace, _text)

class _StopIterationExecution(Exception):
    def __init__(self, message, node_id=None, node_type=None):
        super().__init__(str(message))
        self.message = str(message)
        self.node_id = node_id
        self.node_type = node_type

def _resolve_template(_text, _item):
    if not isinstance(_text, str):
        return _text

    _text = _resolve_secret_placeholders(_text)

    def _replace(_match):
        _name = _match.group(1)
        if _name not in _item:
            raise ValueError(f"Missing variable: {_name}")
        _value = _item.get(_name)
        if _value is None:
            return ""
        return str(_value)

    return _TPL_VAR_RE.sub(_replace, _text)

def _resolve_json_template(_obj, _item):
    if isinstance(_obj, dict):
        return {str(_k): _resolve_json_template(_v, _item) for _k, _v in _obj.items()}
    if isinstance(_obj, list):
        return [_resolve_json_template(_v, _item) for _v in _obj]
    if isinstance(_obj, str):
        _obj = _resolve_secret_placeholders(_obj)
        _m = _TPL_VAR_RE.fullmatch(_obj)
        if _m:
            _name = _m.group(1)
            if _name not in _item:
                raise ValueError(f"Missing variable: {_name}")
            return _item.get(_name)
        return _resolve_template(_obj, _item)
    return _obj

def _resolve_item_path(_item, _path):
    _path = str(_path or "").strip()
    if not _path:
        raise ValueError("Empty path")

    _parts = []
    _buf = ""
    _i = 0
    while _i < len(_path):
        _ch = _path[_i]
        if _ch == '.':
            if _buf:
                _parts.append(_buf)
                _buf = ""
            _i += 1
            continue
        if _ch == '[':
            if _buf:
                _parts.append(_buf)
                _buf = ""
            _j = _path.find(']', _i + 1)
            if _j < 0:
                raise ValueError(f"Invalid path syntax '{_path}'")
            _idx_txt = _path[_i + 1:_j].strip()
            if not _idx_txt.isdigit():
                raise ValueError(f"Invalid path index '{_idx_txt}' in '{_path}'")
            _parts.append(int(_idx_txt))
            _i = _j + 1
            continue
        _buf += _ch
        _i += 1
    if _buf:
        _parts.append(_buf)

    _cur = _item
    for _p in _parts:
        if isinstance(_p, int):
            if not isinstance(_cur, list):
                raise ValueError(f"Path '{_path}' expected list before index [{_p}]")
            if _p < 0 or _p >= len(_cur):
                raise ValueError(f"Path '{_path}' index [{_p}] out of range")
            _cur = _cur[_p]
        else:
            if not isinstance(_cur, dict):
                raise ValueError(f"Path '{_path}' expected object before key '{_p}'")
            if _p not in _cur:
                raise ValueError(f"Path '{_path}' key '{_p}' not found")
            _cur = _cur[_p]
    return _cur

def _validate_target_url(_url):
    _parsed = urlparse(_url)
    if _parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    if not _parsed.hostname:
        raise ValueError("URL hostname is required")

    _host = _parsed.hostname
    try:
        _infos = socket.getaddrinfo(_host, _parsed.port or (_parsed.scheme == "https" and 443 or 80))
    except Exception as _dns_ex:
        raise ValueError(f"Unable to resolve host '{_host}': {_dns_ex}")

    for _info in _infos:
        _ip_txt = _info[4][0]
        try:
            _ip = ipaddress.ip_address(_ip_txt)
        except ValueError:
            continue
        if _ip.is_private or _ip.is_loopback or _ip.is_link_local or _ip.is_multicast or _ip.is_unspecified:
            raise ValueError(f"Blocked target address: {_ip}")

def _decode_http_body(_raw):
    if _raw is None:
        return None
    try:
        _text = _raw.decode("utf-8")
    except Exception:
        _text = _raw.decode("utf-8", errors="replace")
    _text = _text.strip()
    if not _text:
        return None
    try:
        return json.loads(_text)
    except Exception:
        return _text

def _perform_http_request(method, url, headers, body_obj, timeout_seconds):
    _result = {
        "ok": False,
        "status_code": None,
        "response_headers": {},
        "response_body": None,
        "error_message": None,
    }

    _headers = {str(_k): str(_v) for _k, _v in (headers or {}).items()}
    _data = None
    if method == "POST":
        _json_txt = json.dumps(body_obj if body_obj is not None else {})
        _data = _json_txt.encode("utf-8")
        if len(_data) > _MAX_REQUEST_BODY_BYTES:
            raise ValueError(f"Request body too large ({len(_data)} bytes)")
        if "Content-Type" not in _headers and "content-type" not in {k.lower(): k for k in _headers}:
            _headers["Content-Type"] = "application/json"

    _req = _UrlRequest(url=url, method=method, headers=_headers, data=_data)
    try:
        with _urlopen(_req, timeout=float(timeout_seconds)) as _resp:
            _raw = _resp.read(_MAX_RESPONSE_BODY_BYTES + 1)
            if len(_raw) > _MAX_RESPONSE_BODY_BYTES:
                raise ValueError(f"Response body too large (>{_MAX_RESPONSE_BODY_BYTES} bytes)")
            _result["ok"] = 200 <= _resp.status < 300
            _result["status_code"] = int(_resp.status)
            _result["response_headers"] = dict(_resp.headers.items())
            _result["response_body"] = _decode_http_body(_raw)
            if not _result["ok"]:
                _result["error_message"] = f"HTTP {_resp.status}"
    except _HTTPError as _http_ex:
        _raw = _http_ex.read(_MAX_RESPONSE_BODY_BYTES + 1)
        if len(_raw) > _MAX_RESPONSE_BODY_BYTES:
            raise ValueError(f"Response body too large (>{_MAX_RESPONSE_BODY_BYTES} bytes)")
        _result["ok"] = False
        _result["status_code"] = int(_http_ex.code)
        _result["response_headers"] = dict(_http_ex.headers.items()) if _http_ex.headers else {}
        _result["response_body"] = _decode_http_body(_raw)
        _result["error_message"] = f"HTTP {_http_ex.code}"
    except TimeoutError:
        _result["ok"] = False
        _result["error_message"] = f"Request timeout after {timeout_seconds}s"
    except _URLError as _url_ex:
        _result["ok"] = False
        _result["error_message"] = f"Network error: {_url_ex.reason}"

    return _result
'''

WORKFLOW_MAIN_START = '''\
def _run():
    global _items, _final_output
'''

WORKFLOW_MAIN_END = '''\
if __name__ == "__main__":
    try:
        _run()
    except _StopIterationExecution as _stop_ex:
        _final_output = {
            'status': 'stopped_current_execution',
            'stop_reason': _stop_ex.message,
            'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type},
            'mode': 'stopped',
            'branches': {},
            'terminals': [],
            'legacy_items': [],
        }
    except Exception as _exc:
        _logger.error("Unhandled exception:\\n%s", traceback.format_exc())
        print(f"ERROR: {_exc}  (see {_log_path})", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(_final_output, default=str))
'''


def _build_node(node_data: dict) -> BaseNode:
    node_type = node_data["type"]
    cls = NODE_REGISTRY.get(node_type)
    if cls is None:
        raise ValueError(f"Unknown node type: '{node_type}'")
    return cls(node_id=node_data["id"], config=node_data.get("config", {}))


def _topological_waves(nodes: list[dict], edges: list[dict]) -> list[list[dict]]:
    """
    Returns nodes grouped into execution waves using Kahn's BFS algorithm.

    Each wave is a list of nodes that can run concurrently — they share no
    dependency between each other within the same wave.  Waves must be executed
    in order: wave N must complete before wave N+1 starts.

    Raises ValueError if the graph contains a cycle.
    """
    node_map = {n["id"]: n for n in nodes}
    in_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        src = edge["source_node_id"]
        tgt = edge["target_node_id"]
        adjacency[src].append(tgt)
        in_degree[tgt] += 1

    # Seed with all nodes that have no predecessors
    current_wave_ids: list[str] = [
        node_id for node_id in node_map if in_degree[node_id] == 0
    ]
    waves: list[list[dict]] = []
    visited = 0

    while current_wave_ids:
        waves.append([node_map[nid] for nid in current_wave_ids])
        visited += len(current_wave_ids)
        next_wave_ids: list[str] = []
        for node_id in current_wave_ids:
            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_wave_ids.append(neighbor)
        current_wave_ids = next_wave_ids

    if visited != len(nodes):
        raise ValueError("Workflow contains a cycle — cannot generate code")

    return waves


def _emit_waves(
    waves: list[list[dict]],
    edges: list[dict],
    base_indent: int,
    lines: list[str],
    instrument: bool = False,
) -> None:
    """
    Emit Python source lines for a sequence of waves at the given base indent.

    - A wave with a single node is emitted inline (no threading overhead).
    - A wave with multiple nodes is wrapped in a ThreadPoolExecutor block so
      all branches in that wave run concurrently. Each branch resolves its own
      input from predecessor node outputs.
    - Branches stay isolated until an explicit merge node combines them.
    - When instrument=True, each node's execution is wrapped with items snapshot
      that appends a trace entry to the global _trace list.
    """
    if not waves:
        return

    subset_nodes = [node_data for wave in waves for node_data in wave]
    subset_node_map = {node_data["id"]: node_data for node_data in subset_nodes}
    subset_node_ids = [node_data["id"] for node_data in subset_nodes]
    subset_node_ids_set = set(subset_node_ids)

    incoming_map: dict[str, list[tuple[str, str]]] = {node_id: [] for node_id in subset_node_ids}
    outgoing_internal_count: dict[str, int] = {node_id: 0 for node_id in subset_node_ids}
    adjacency_internal: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge["source_node_id"]
        tgt = edge["target_node_id"]
        if src in subset_node_ids_set and tgt in subset_node_ids_set:
            src_output = str(edge.get("source_output") or "output_1")
            pred = (src, src_output)
            if pred not in incoming_map[tgt]:
                incoming_map[tgt].append(pred)
            outgoing_internal_count[src] += 1
            adjacency_internal[src].append(tgt)

    terminal_node_ids = [
        node_id for node_id in subset_node_ids if outgoing_internal_count[node_id] == 0
    ]

    terminal_node_meta = {
        node_id: {
            "id": node_id,
            "label": subset_node_map[node_id].get("label", node_id),
            "type": subset_node_map[node_id]["type"],
        }
        for node_id in terminal_node_ids
    }

    pad = " " * base_indent
    lines.append(f"{pad}_items_seed = list(_items)")
    lines.append(f"{pad}_node_items = {{}}")
    lines.append(f"{pad}_node_outputs = {{}}")
    lines.append("")

    def _emit_node_input_setup(node_data: dict, indent: int) -> list[str]:
        node_id = node_data["id"]
        preds = incoming_map.get(node_id, [])
        line_prefix = " " * indent
        out: list[str] = []

        if not preds:
            out.append(f"{line_prefix}_items = list(_items_seed)")
            return out

        if len(preds) == 1:
            pred_id, pred_output = preds[0]
            out.append(f"{line_prefix}_pred_outputs = _node_outputs.get({pred_id!r}, {{}})")
            out.append(
                f"{line_prefix}_items = list(_pred_outputs.get({pred_output!r}, _pred_outputs.get('output_1', [])))"
            )
            return out

        if node_data["type"] == MergeNode.NODE_TYPE:
            out.append(f"{line_prefix}_items = []")
            for pred_id, pred_output in preds:
                out.append(f"{line_prefix}_pred_outputs = _node_outputs.get({pred_id!r}, {{}})")
                out.append(
                    f"{line_prefix}_items.extend(list(_pred_outputs.get({pred_output!r}, _pred_outputs.get('output_1', []))))"
                )
            return out

        pred_id, pred_output = preds[0]
        out.append(f"{line_prefix}_pred_outputs = _node_outputs.get({pred_id!r}, {{}})")
        out.append(
            f"{line_prefix}_items = list(_pred_outputs.get({pred_output!r}, _pred_outputs.get('output_1', [])))"
        )
        return out

    for w_idx, wave in enumerate(waves):
        if len(wave) == 1:
            node_data = wave[0]
            node = _build_node(node_data)
            node_id = node_data["id"]
            node_type = node_data["type"]
            node_label = node_data.get("label", node_type)

            # Scheduler nodes don't use the item loop pattern
            if node_type == SchedulerNode.NODE_TYPE:
                lines.append(node.to_code(indent=base_indent))
                lines.append("")
                continue

            lines.extend(_emit_node_input_setup(node_data, base_indent))
            lines.append(f"{pad}_branch_outputs = None")
            lines.append(f"{pad}_node_debug = None")

            if instrument:
                lines.append(f"{pad}_items_before = list(_items)")
                lines.append(f"{pad}try:")
                lines.append(node.to_code(indent=base_indent + 4))
                lines.append(f"{pad}    _items_after = list(_items)")
                lines.append(f"{pad}    _node_outputs_raw = _branch_outputs if isinstance(_branch_outputs, dict) else {{'output_1': _items_after}}")
                lines.append(f"{pad}    _node_outputs_norm = {{}}")
                lines.append(f"{pad}    for _out_name, _out_items in _node_outputs_raw.items():")
                lines.append(f"{pad}        if _out_items is None:")
                lines.append(f"{pad}            _node_outputs_norm[str(_out_name)] = []")
                lines.append(f"{pad}        elif isinstance(_out_items, list):")
                lines.append(f"{pad}            _node_outputs_norm[str(_out_name)] = list(_out_items)")
                lines.append(f"{pad}        else:")
                lines.append(f"{pad}            raise ValueError(f\"[{node_label}] node output '{{_out_name}}' must be a list\")")
                lines.append(f"{pad}    if 'output_1' not in _node_outputs_norm:")
                lines.append(f"{pad}        _node_outputs_norm['output_1'] = list(_items_after)")
                lines.append(f"{pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'ok', 'ts': time.time(), 'items_in': _items_before, 'items_out': _items_after, 'debug': _node_debug}})")
                lines.append(f"{pad}    _node_items[{node_id!r}] = _items_after")
                lines.append(f"{pad}    _node_outputs[{node_id!r}] = _node_outputs_norm")
                lines.append(f"{pad}except _StopIterationExecution as _stop_ex:")
                lines.append(f"{pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'stopped_current_execution', 'ts': time.time(), 'items_in': _items_before, 'error': _stop_ex.message}})")
                lines.append(f"{pad}    raise")
                lines.append(f"{pad}except Exception as _tr_ex:")
                lines.append(f"{pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'error', 'ts': time.time(), 'items_in': _items_before, 'error': str(_tr_ex)}})")
                lines.append(f"{pad}    raise")
                lines.append("")
            else:
                lines.append(node.to_code(indent=base_indent))
                lines.append(f"{pad}_items_after = list(_items)")
                lines.append(f"{pad}_node_outputs_raw = _branch_outputs if isinstance(_branch_outputs, dict) else {{'output_1': _items_after}}")
                lines.append(f"{pad}_node_outputs_norm = {{}}")
                lines.append(f"{pad}for _out_name, _out_items in _node_outputs_raw.items():")
                lines.append(f"{pad}    if _out_items is None:")
                lines.append(f"{pad}        _node_outputs_norm[str(_out_name)] = []")
                lines.append(f"{pad}    elif isinstance(_out_items, list):")
                lines.append(f"{pad}        _node_outputs_norm[str(_out_name)] = list(_out_items)")
                lines.append(f"{pad}    else:")
                lines.append(f"{pad}        raise ValueError(f\"[{node_label}] node output '{{_out_name}}' must be a list\")")
                lines.append(f"{pad}if 'output_1' not in _node_outputs_norm:")
                lines.append(f"{pad}    _node_outputs_norm['output_1'] = list(_items_after)")
                lines.append(f"{pad}_node_items[{node_id!r}] = _items_after")
                lines.append(f"{pad}_node_outputs[{node_id!r}] = _node_outputs_norm")
                lines.append("")
        else:
            # Multi-node wave: each branch resolves inputs from its own predecessors.
            branch_names: list[str] = []
            lines.append(f"{pad}_wave_{w_idx}_results = [None] * {len(wave)}")
            for b_idx, node_data in enumerate(wave):
                fn_name = f"_wave_{w_idx}_branch_{b_idx}"
                branch_names.append(fn_name)
                node = _build_node(node_data)
                node_id = node_data["id"]
                node_type = node_data["type"]
                node_label = node_data.get("label", node_type)

                lines.append(f"{pad}def {fn_name}():")

                lines.extend(_emit_node_input_setup(node_data, base_indent + 4))
                inner_pad = " " * (base_indent + 4)
                lines.append(f"{inner_pad}_branch_outputs = None")
                lines.append(f"{inner_pad}_node_debug = None")

                if instrument:
                    lines.append(f"{inner_pad}_items_before = list(_items)")
                    lines.append(f"{inner_pad}try:")
                    lines.append(node.to_code(indent=base_indent + 8))
                    lines.append(f"{inner_pad}    _items_after = list(_items)")
                    lines.append(f"{inner_pad}    _node_outputs_raw = _branch_outputs if isinstance(_branch_outputs, dict) else {{'output_1': _items_after}}")
                    lines.append(f"{inner_pad}    _node_outputs_norm = {{}}")
                    lines.append(f"{inner_pad}    for _out_name, _out_items in _node_outputs_raw.items():")
                    lines.append(f"{inner_pad}        if _out_items is None:")
                    lines.append(f"{inner_pad}            _node_outputs_norm[str(_out_name)] = []")
                    lines.append(f"{inner_pad}        elif isinstance(_out_items, list):")
                    lines.append(f"{inner_pad}            _node_outputs_norm[str(_out_name)] = list(_out_items)")
                    lines.append(f"{inner_pad}        else:")
                    lines.append(f"{inner_pad}            raise ValueError(f\"[{node_label}] node output '{{_out_name}}' must be a list\")")
                    lines.append(f"{inner_pad}    if 'output_1' not in _node_outputs_norm:")
                    lines.append(f"{inner_pad}        _node_outputs_norm['output_1'] = list(_items_after)")
                    lines.append(f"{inner_pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'ok', 'ts': time.time(), 'items_in': _items_before, 'items_out': _items_after, 'debug': _node_debug}})")
                    lines.append(f"{inner_pad}    _wave_{w_idx}_results[{b_idx}] = {{'items': _items_after, 'outputs': _node_outputs_norm, 'debug': _node_debug}}")
                    lines.append(f"{inner_pad}except _StopIterationExecution as _stop_ex:")
                    lines.append(f"{inner_pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'stopped_current_execution', 'ts': time.time(), 'items_in': _items_before, 'error': _stop_ex.message}})")
                    lines.append(f"{inner_pad}    raise")
                    lines.append(f"{inner_pad}except Exception as _tr_ex:")
                    lines.append(f"{inner_pad}    _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'error', 'ts': time.time(), 'items_in': _items_before, 'error': str(_tr_ex)}})")
                    lines.append(f"{inner_pad}    raise")
                else:
                    lines.append(node.to_code(indent=base_indent + 4))
                    lines.append(f"{inner_pad}_items_after = list(_items)")
                    lines.append(f"{inner_pad}_node_outputs_raw = _branch_outputs if isinstance(_branch_outputs, dict) else {{'output_1': _items_after}}")
                    lines.append(f"{inner_pad}_node_outputs_norm = {{}}")
                    lines.append(f"{inner_pad}for _out_name, _out_items in _node_outputs_raw.items():")
                    lines.append(f"{inner_pad}    if _out_items is None:")
                    lines.append(f"{inner_pad}        _node_outputs_norm[str(_out_name)] = []")
                    lines.append(f"{inner_pad}    elif isinstance(_out_items, list):")
                    lines.append(f"{inner_pad}        _node_outputs_norm[str(_out_name)] = list(_out_items)")
                    lines.append(f"{inner_pad}    else:")
                    lines.append(f"{inner_pad}        raise ValueError(f\"[{node_label}] node output '{{_out_name}}' must be a list\")")
                    lines.append(f"{inner_pad}if 'output_1' not in _node_outputs_norm:")
                    lines.append(f"{inner_pad}    _node_outputs_norm['output_1'] = list(_items_after)")
                    lines.append(f"{inner_pad}_wave_{w_idx}_results[{b_idx}] = {{'items': _items_after, 'outputs': _node_outputs_norm, 'debug': _node_debug}}")
                lines.append("")

            submits = ", ".join(
                f"_pool.submit({fn})" for fn in branch_names
            )
            lines.append(f"{pad}with _TPE() as _pool:")
            lines.append(f"{pad}    _futs = [{submits}]")
            lines.append(f"{pad}    _done, _ = _wait(_futs, return_when=_ALL)")
            lines.append(f"{pad}    for _f in _done:")
            lines.append(f"{pad}        _f.result()  # re-raises branch exceptions")
            for b_idx, node_data in enumerate(wave):
                node_id = node_data["id"]
                lines.append(
                    f"{pad}_node_items[{node_id!r}] = (_wave_{w_idx}_results[{b_idx}] or {{}}).get('items', [])"
                )
                lines.append(
                    f"{pad}_node_outputs[{node_id!r}] = (_wave_{w_idx}_results[{b_idx}] or {{}}).get('outputs', {{'output_1': []}})"
                )
            lines.append("")

    lines.append(f"{pad}_terminal_node_ids = {terminal_node_ids!r}")
    lines.append(f"{pad}_terminal_node_meta = {terminal_node_meta!r}")
    lines.append(f"{pad}_terminal_branches = {{}}")
    for node_id in terminal_node_ids:
        lines.append(f"{pad}_terminal_branches[{node_id!r}] = list(_node_items.get({node_id!r}, []))")

    lines.append(f"{pad}_items = []")
    for node_id in terminal_node_ids:
        lines.append(f"{pad}_items.extend(_terminal_branches[{node_id!r}])")

    lines.append(
        f"{pad}_final_output = {{'mode': 'by_terminal_branch', 'branches': _terminal_branches, 'terminals': [_terminal_node_meta[_tid] for _tid in _terminal_node_ids], 'legacy_items': list(_items)}}"
    )
    lines.append("")


def validate_graph(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Validate all nodes and return a flat list of error messages."""
    errors: list[str] = []

    if not nodes:
        errors.append("Workflow has no nodes")
        return errors

    # Detect multiple scheduler nodes
    scheduler_nodes = [n for n in nodes if n["type"] == SchedulerNode.NODE_TYPE]
    if len(scheduler_nodes) > 1:
        errors.append("Only one Scheduler node is allowed per workflow")

    incoming_count: dict[str, int] = defaultdict(int)
    for edge in edges:
        incoming_count[edge["target_node_id"]] += 1

    for node_data in nodes:
        node_id = node_data["id"]
        if incoming_count[node_id] > 1 and node_data["type"] != MergeNode.NODE_TYPE:
            errors.append(
                f"[{node_data.get('label', node_id)}] "
                f"Only 'merge' nodes can have multiple incoming edges "
                f"(has {incoming_count[node_id]})"
            )

    for node_data in nodes:
        if node_data["type"] != MergeNode.NODE_TYPE:
            continue
        node_id = node_data["id"]
        raw_branch_count = node_data.get("config", {}).get("branch_count", 2)
        try:
            branch_count = int(raw_branch_count)
        except (TypeError, ValueError):
            continue
        current_incoming = incoming_count[node_id]
        if current_incoming != branch_count:
            node_label = node_data.get("label", node_id)
            errors.append(
                f"[{node_label}] merge requires {branch_count} incoming edges "
                f"(has {current_incoming})"
            )

    # Per-node validation
    for node_data in nodes:
        try:
            node = _build_node(node_data)
            node_errors = node.validate()
            for err in node_errors:
                errors.append(f"[{node_data.get('label', node_data['id'])}] {err}")
        except ValueError as exc:
            errors.append(str(exc))

    # Check for cycles via topological waves
    try:
        _topological_waves(nodes, edges)
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def generate_script(workflow_name: str, workflow_id: str, nodes: list[dict], edges: list[dict]) -> str:
    """
    Generate a standalone Python script from the workflow graph.
    Independent branches at the same topological level are executed in parallel.
    Returns the script as a string.
    """
    errors = validate_graph(nodes, edges)
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    waves = _topological_waves(nodes, edges)

    # WORKFLOW_NAME and WORKFLOW_ID must be defined before the logging setup in SCRIPT_HEADER
    lines: list[str] = [
        f'WORKFLOW_NAME = {repr(workflow_name)}',
        f'WORKFLOW_ID = {repr(workflow_id)}\n',
    ]
    lines.append(SCRIPT_HEADER)

    # Initialize _items array with workflow context
    lines.append("# ---- Initialize items array ----")
    lines.append("EXECUTION_ID = str(uuid.uuid4())")
    lines.append("_secret_store = {}")
    lines.append("_items = [{")
    lines.append('    "workflowId": WORKFLOW_ID,')
    lines.append('    "executionId": EXECUTION_ID,')
    lines.append('    "executionDate": datetime.now(timezone.utc).isoformat()')
    lines.append("}]\n")

    # Locate the wave that contains the Scheduler node (if any).
    # The scheduler must be alone in its wave (it opens the while-True block).
    scheduler_wave_idx: Optional[int] = None
    for w_idx, wave in enumerate(waves):
        for node_data in wave:
            if node_data["type"] == SchedulerNode.NODE_TYPE:
                scheduler_wave_idx = w_idx
                break
        if scheduler_wave_idx is not None:
            break

    # All workflow logic goes inside _run() so errors are caught at the top level
    lines.append(WORKFLOW_MAIN_START)  # "def _run():"

    if scheduler_wave_idx is not None:
        # Waves before the scheduler → setup code (indent=4, inside _run)
        if waves[:scheduler_wave_idx]:
            lines.append("    try:")
            _emit_waves(waves[:scheduler_wave_idx], edges=edges, base_indent=8, lines=lines)
            lines.append("    except _StopIterationExecution as _stop_ex:")
            lines.append("        _final_output = {'status': 'stopped_current_execution', 'stop_reason': _stop_ex.message, 'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type}, 'mode': 'stopped', 'branches': {}, 'terminals': [], 'legacy_items': []}")
            lines.append("        return")
            lines.append("")

        # Scheduler wave: find the node and emit the while-True header
        sched_wave = waves[scheduler_wave_idx]
        sched_node_data = next(
            nd for nd in sched_wave if nd["type"] == SchedulerNode.NODE_TYPE
        )
        sched_node = cast(SchedulerNode, _build_node(sched_node_data))
        lines.append(sched_node.to_code(indent=4))  # "    while True:"
        lines.append("")

        # Reset execution context on each scheduler tick
        lines.append("        EXECUTION_ID = str(uuid.uuid4())")
        lines.append("        _secret_store = {}")
        lines.append("        _items = [{")
        lines.append('            "workflowId": WORKFLOW_ID,')
        lines.append('            "executionId": EXECUTION_ID,')
        lines.append('            "executionDate": datetime.now(timezone.utc).isoformat()')
        lines.append("        }]")
        lines.append("        _final_output = {}")
        lines.append("")

        # Waves after the scheduler → loop body (indent=8, inside while True)
        post_scheduler_waves = waves[scheduler_wave_idx + 1:]
        if post_scheduler_waves:
            lines.append("        try:")
            _emit_waves(post_scheduler_waves, edges=edges, base_indent=12, lines=lines)
            lines.append("        except _StopIterationExecution as _stop_ex:")
            lines.append("            _final_output = {'status': 'stopped_current_execution', 'stop_reason': _stop_ex.message, 'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type}, 'mode': 'stopped', 'branches': {}, 'terminals': [], 'legacy_items': []}")
            lines.append("")

        # Close the loop with time.sleep (indent=4 inside _run)
        lines.append(sched_node.loop_close_code(indent=4))
        lines.append("        print(json.dumps(_final_output, default=str))")
        lines.append("")

    else:
        # No scheduler — all waves run sequentially inside _run (indent=4)
        lines.append("    try:")
        _emit_waves(waves, edges=edges, base_indent=8, lines=lines)
        lines.append("    except _StopIterationExecution as _stop_ex:")
        lines.append("        _final_output = {'status': 'stopped_current_execution', 'stop_reason': _stop_ex.message, 'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type}, 'mode': 'stopped', 'branches': {}, 'terminals': [], 'legacy_items': []}")

    lines.append(WORKFLOW_MAIN_END)

    return "\n".join(lines)


RUN_SCRIPT_HEADER = '''\
# ============================================================
# Auto-generated workflow run script (instrumented)
# ============================================================
import sys
import os
import json
import time
import uuid
import re
import base64
import hashlib
import hmac
import socket
import ipaddress
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor as _TPE, wait as _wait, ALL_COMPLETED as _ALL
from urllib.parse import urlparse
from urllib.parse import urlencode as _urlencode
from urllib.request import Request as _UrlRequest, urlopen as _urlopen
from urllib.error import HTTPError as _HTTPError, URLError as _URLError

_trace = []
_trace_path = os.environ.get("WORKFLOW_TRACE_PATH", "")
_final_output = {}
_final_output_path = os.environ.get("WORKFLOW_FINAL_OUTPUT_PATH", "")

_TPL_VAR_RE = re.compile(r"\\$\\{([A-Za-z_][A-Za-z0-9_]*)\\}")
_SECRET_VAR_RE = re.compile(r"#\\{([A-Za-z_][A-Za-z0-9_]*)\\}")
_MAX_REQUEST_BODY_BYTES = 1_000_000
_MAX_RESPONSE_BODY_BYTES = 2_000_000
_SECRET_PREFIX = "enc:v1:"
_secret_store = {}

def _load_master_key():
    _raw = os.environ.get("W_METADATA_1", "").strip()
    if not _raw:
        raise ValueError("Missing required environment variable: W_METADATA_1")
    return _raw.encode("utf-8")

def _derive_stream_key(_master_key, _salt):
    return hashlib.pbkdf2_hmac("sha256", _master_key, _salt, 120000, dklen=32)

def _xor_bytes(_data, _stream):
    _out = bytearray(len(_data))
    _stream_len = len(_stream)
    for _idx, _byte in enumerate(_data):
        _out[_idx] = _byte ^ _stream[_idx % _stream_len]
    return bytes(_out)

def _decrypt_secret_value(_ciphertext):
    if not isinstance(_ciphertext, str) or not _ciphertext.startswith(_SECRET_PREFIX):
        raise ValueError("Invalid encrypted secret format")
    _payload_b64 = _ciphertext[len(_SECRET_PREFIX):]
    try:
        _payload = base64.urlsafe_b64decode(_payload_b64.encode("ascii"))
    except Exception as _ex:
        raise ValueError("Invalid encrypted secret payload") from _ex
    if len(_payload) < 48:
        raise ValueError("Encrypted secret payload is too short")

    _salt = _payload[:16]
    _mac = _payload[16:48]
    _cipher_bytes = _payload[48:]
    _master_key = _load_master_key()
    _expected_mac = hmac.new(_master_key, _salt + _cipher_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(_mac, _expected_mac):
        raise ValueError("Secret integrity check failed")

    _stream = _derive_stream_key(_master_key, _salt)
    _plain = _xor_bytes(_cipher_bytes, _stream)
    try:
        return _plain.decode("utf-8")
    except Exception as _ex:
        raise ValueError("Decrypted secret is not valid UTF-8") from _ex

def _resolve_secret_placeholders(_text):
    if not isinstance(_text, str):
        return _text

    def _replace(_match):
        _name = _match.group(1)
        if _name not in _secret_store:
            raise ValueError(f"Missing secret: {_name}")
        _value = _secret_store.get(_name)
        if _value is None:
            return ""
        return str(_value)

    return _SECRET_VAR_RE.sub(_replace, _text)

class _StopIterationExecution(Exception):
    def __init__(self, message, node_id=None, node_type=None):
        super().__init__(str(message))
        self.message = str(message)
        self.node_id = node_id
        self.node_type = node_type

def _resolve_template(_text, _item):
    if not isinstance(_text, str):
        return _text

    _text = _resolve_secret_placeholders(_text)

    def _replace(_match):
        _name = _match.group(1)
        if _name not in _item:
            raise ValueError(f"Missing variable: {_name}")
        _value = _item.get(_name)
        if _value is None:
            return ""
        return str(_value)

    return _TPL_VAR_RE.sub(_replace, _text)

def _resolve_json_template(_obj, _item):
    if isinstance(_obj, dict):
        return {str(_k): _resolve_json_template(_v, _item) for _k, _v in _obj.items()}
    if isinstance(_obj, list):
        return [_resolve_json_template(_v, _item) for _v in _obj]
    if isinstance(_obj, str):
        _obj = _resolve_secret_placeholders(_obj)
        _m = _TPL_VAR_RE.fullmatch(_obj)
        if _m:
            _name = _m.group(1)
            if _name not in _item:
                raise ValueError(f"Missing variable: {_name}")
            return _item.get(_name)
        return _resolve_template(_obj, _item)
    return _obj

def _resolve_item_path(_item, _path):
    _path = str(_path or "").strip()
    if not _path:
        raise ValueError("Empty path")

    _parts = []
    _buf = ""
    _i = 0
    while _i < len(_path):
        _ch = _path[_i]
        if _ch == '.':
            if _buf:
                _parts.append(_buf)
                _buf = ""
            _i += 1
            continue
        if _ch == '[':
            if _buf:
                _parts.append(_buf)
                _buf = ""
            _j = _path.find(']', _i + 1)
            if _j < 0:
                raise ValueError(f"Invalid path syntax '{_path}'")
            _idx_txt = _path[_i + 1:_j].strip()
            if not _idx_txt.isdigit():
                raise ValueError(f"Invalid path index '{_idx_txt}' in '{_path}'")
            _parts.append(int(_idx_txt))
            _i = _j + 1
            continue
        _buf += _ch
        _i += 1
    if _buf:
        _parts.append(_buf)

    _cur = _item
    for _p in _parts:
        if isinstance(_p, int):
            if not isinstance(_cur, list):
                raise ValueError(f"Path '{_path}' expected list before index [{_p}]")
            if _p < 0 or _p >= len(_cur):
                raise ValueError(f"Path '{_path}' index [{_p}] out of range")
            _cur = _cur[_p]
        else:
            if not isinstance(_cur, dict):
                raise ValueError(f"Path '{_path}' expected object before key '{_p}'")
            if _p not in _cur:
                raise ValueError(f"Path '{_path}' key '{_p}' not found")
            _cur = _cur[_p]
    return _cur

def _validate_target_url(_url):
    _parsed = urlparse(_url)
    if _parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    if not _parsed.hostname:
        raise ValueError("URL hostname is required")

    _host = _parsed.hostname
    try:
        _infos = socket.getaddrinfo(_host, _parsed.port or (_parsed.scheme == "https" and 443 or 80))
    except Exception as _dns_ex:
        raise ValueError(f"Unable to resolve host '{_host}': {_dns_ex}")

    for _info in _infos:
        _ip_txt = _info[4][0]
        try:
            _ip = ipaddress.ip_address(_ip_txt)
        except ValueError:
            continue
        if _ip.is_private or _ip.is_loopback or _ip.is_link_local or _ip.is_multicast or _ip.is_unspecified:
            raise ValueError(f"Blocked target address: {_ip}")

def _decode_http_body(_raw):
    if _raw is None:
        return None
    try:
        _text = _raw.decode("utf-8")
    except Exception:
        _text = _raw.decode("utf-8", errors="replace")
    _text = _text.strip()
    if not _text:
        return None
    try:
        return json.loads(_text)
    except Exception:
        return _text

def _perform_http_request(method, url, headers, body_obj, timeout_seconds):
    _result = {
        "ok": False,
        "status_code": None,
        "response_headers": {},
        "response_body": None,
        "error_message": None,
    }

    _headers = {str(_k): str(_v) for _k, _v in (headers or {}).items()}
    _data = None
    if method == "POST":
        _json_txt = json.dumps(body_obj if body_obj is not None else {})
        _data = _json_txt.encode("utf-8")
        if len(_data) > _MAX_REQUEST_BODY_BYTES:
            raise ValueError(f"Request body too large ({len(_data)} bytes)")
        if "Content-Type" not in _headers and "content-type" not in {k.lower(): k for k in _headers}:
            _headers["Content-Type"] = "application/json"

    _req = _UrlRequest(url=url, method=method, headers=_headers, data=_data)
    try:
        with _urlopen(_req, timeout=float(timeout_seconds)) as _resp:
            _raw = _resp.read(_MAX_RESPONSE_BODY_BYTES + 1)
            if len(_raw) > _MAX_RESPONSE_BODY_BYTES:
                raise ValueError(f"Response body too large (>{_MAX_RESPONSE_BODY_BYTES} bytes)")
            _result["ok"] = 200 <= _resp.status < 300
            _result["status_code"] = int(_resp.status)
            _result["response_headers"] = dict(_resp.headers.items())
            _result["response_body"] = _decode_http_body(_raw)
            if not _result["ok"]:
                _result["error_message"] = f"HTTP {_resp.status}"
    except _HTTPError as _http_ex:
        _raw = _http_ex.read(_MAX_RESPONSE_BODY_BYTES + 1)
        if len(_raw) > _MAX_RESPONSE_BODY_BYTES:
            raise ValueError(f"Response body too large (>{_MAX_RESPONSE_BODY_BYTES} bytes)")
        _result["ok"] = False
        _result["status_code"] = int(_http_ex.code)
        _result["response_headers"] = dict(_http_ex.headers.items()) if _http_ex.headers else {}
        _result["response_body"] = _decode_http_body(_raw)
        _result["error_message"] = f"HTTP {_http_ex.code}"
    except TimeoutError:
        _result["ok"] = False
        _result["error_message"] = f"Request timeout after {timeout_seconds}s"
    except _URLError as _url_ex:
        _result["ok"] = False
        _result["error_message"] = f"Network error: {_url_ex.reason}"

    return _result

def _write_traces():
    if _trace_path:
        try:
            with open(_trace_path, "w", encoding="utf-8") as _f:
                json.dump(_trace, _f, default=str, indent=2)
        except Exception:
            pass

def _write_final_output():
    if _final_output_path:
        try:
            with open(_final_output_path, "w", encoding="utf-8") as _f:
                json.dump(_final_output, _f, default=str, indent=2)
        except Exception:
            pass
'''


def generate_run_script(workflow_name: str, workflow_id: str, nodes: list[dict], edges: list[dict]) -> str:
    """
    Generate an instrumented Python script for one-time workflow execution.
    Each node's input/output items are captured and written to a trace file.

    The trace file path is passed via the WORKFLOW_TRACE_PATH environment variable.
    Returns the script as a string.
    """
    errors = validate_graph(nodes, edges)
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    waves = _topological_waves(nodes, edges)

    lines: list[str] = [
        f'WORKFLOW_NAME = {repr(workflow_name)}',
        f'WORKFLOW_ID = {repr(workflow_id)}\n',
    ]
    lines.append(RUN_SCRIPT_HEADER)

    # Initialize _items array with workflow context
    lines.append("# ---- Initialize items array ----")
    lines.append("EXECUTION_ID = str(uuid.uuid4())")
    lines.append("_secret_store = {}")
    lines.append("_items = [{")
    lines.append('    "workflowId": WORKFLOW_ID,')
    lines.append('    "executionId": EXECUTION_ID,')
    lines.append('    "executionDate": datetime.now(timezone.utc).isoformat()')
    lines.append("}]\n")

    scheduler_wave_idx: Optional[int] = None
    for w_idx, wave in enumerate(waves):
        for node_data in wave:
            if node_data["type"] == SchedulerNode.NODE_TYPE:
                scheduler_wave_idx = w_idx
                break
        if scheduler_wave_idx is not None:
            break

    lines.append("def _run():")
    lines.append("    global _trace, _items, _final_output")
    lines.append("")

    if scheduler_wave_idx is not None:
        if waves[:scheduler_wave_idx]:
            lines.append("    try:")
            _emit_waves(waves[:scheduler_wave_idx], edges=edges, base_indent=8, lines=lines,
                          instrument=True)
            lines.append("    except _StopIterationExecution as _stop_ex:")
            lines.append("        _final_output = {'status': 'stopped_current_execution', 'stop_reason': _stop_ex.message, 'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type}, 'mode': 'stopped', 'branches': {}, 'terminals': [], 'legacy_items': []}")
            lines.append("        return")
            lines.append("")

        sched_wave = waves[scheduler_wave_idx]
        sched_node_data = next(
            nd for nd in sched_wave if nd["type"] == SchedulerNode.NODE_TYPE
        )
        sched_node = _build_node(sched_node_data)
        node_id = sched_node_data["id"]
        node_type = sched_node_data["type"]
        node_label = sched_node_data.get("label", node_type)

        lines.append(f"    _items_before = list(_items)")
        lines.append("    try:")
        lines.append("        for _run_iter in range(1):")
        lines.append(f"            _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'ok', 'ts': time.time(), 'items_in': _items_before, 'items_out': list(_items)}})")

        post_scheduler_waves = waves[scheduler_wave_idx + 1:]
        if post_scheduler_waves:
            lines.append("        try:")
            _emit_waves(post_scheduler_waves, edges=edges, base_indent=12, lines=lines,
                          instrument=True)
            lines.append("        except _StopIterationExecution as _stop_ex:")
            lines.append("            _final_output = {'status': 'stopped_current_execution', 'stop_reason': _stop_ex.message, 'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type}, 'mode': 'stopped', 'branches': {}, 'terminals': [], 'legacy_items': []}")
            lines.append("")

        lines.append("    except Exception as _tr_ex:")
        lines.append(f"        _trace.append({{'id': {node_id!r}, 'type': {node_type!r}, 'label': {node_label!r}, 'status': 'error', 'items_in': _items_before, 'error': str(_tr_ex)}})")
        lines.append("        raise")
        lines.append("")
    else:
        lines.append("    try:")
        _emit_waves(waves, edges=edges, base_indent=8, lines=lines, instrument=True)
        lines.append("    except _StopIterationExecution as _stop_ex:")
        lines.append("        _final_output = {'status': 'stopped_current_execution', 'stop_reason': _stop_ex.message, 'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type}, 'mode': 'stopped', 'branches': {}, 'terminals': [], 'legacy_items': []}")

    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    try:")
    lines.append("        _run()")
    lines.append("    except _StopIterationExecution as _stop_ex:")
    lines.append("        _final_output = {'status': 'stopped_current_execution', 'stop_reason': _stop_ex.message, 'stop_node': {'id': _stop_ex.node_id, 'type': _stop_ex.node_type}, 'mode': 'stopped', 'branches': {}, 'terminals': [], 'legacy_items': []}")
    lines.append("    except Exception as _tr_ex:")
    lines.append("        if not _trace or _trace[-1].get('status') != 'error':")
    lines.append("            _trace.append({'status': 'fatal', 'error': str(_tr_ex)})")
    lines.append("    finally:")
    lines.append("        _write_traces()")
    lines.append("        _write_final_output()")
    lines.append("    print(json.dumps(_final_output, default=str))")

    return "\n".join(lines)
