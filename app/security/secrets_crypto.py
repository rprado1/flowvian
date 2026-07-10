from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Optional


ENV_MASTER_KEY = "WBUI_METADATA_1"
ENCRYPTED_PREFIX = "enc:v1:"
SECRET_MASK = "********"


def _load_master_key() -> bytes:
    raw = os.environ.get(ENV_MASTER_KEY, "")
    key = raw.strip()
    if not key:
        raise ValueError(f"Missing required environment variable: {ENV_MASTER_KEY}")
    return key.encode("utf-8")


def _derive_stream_key(master_key: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", master_key, salt, 120_000, dklen=32)


def _xor_bytes(data: bytes, key_stream: bytes) -> bytes:
    out = bytearray(len(data))
    key_len = len(key_stream)
    for idx, b in enumerate(data):
        out[idx] = b ^ key_stream[idx % key_len]
    return bytes(out)


def is_encrypted_secret_value(value: object) -> bool:
    return isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX)


def encrypt_secret_value(plaintext: object) -> str:
    if plaintext is None:
        source = ""
    else:
        source = str(plaintext)

    master_key = _load_master_key()
    salt = os.urandom(16)
    stream_key = _derive_stream_key(master_key, salt)
    cipher_bytes = _xor_bytes(source.encode("utf-8"), stream_key)
    mac = hmac.new(master_key, salt + cipher_bytes, hashlib.sha256).digest()
    payload = base64.urlsafe_b64encode(salt + mac + cipher_bytes).decode("ascii")
    return ENCRYPTED_PREFIX + payload


def decrypt_secret_value(ciphertext: object) -> str:
    if not isinstance(ciphertext, str) or not ciphertext.startswith(ENCRYPTED_PREFIX):
        raise ValueError("Invalid encrypted secret format")

    payload_b64 = ciphertext[len(ENCRYPTED_PREFIX):]
    try:
        payload = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
    except Exception as exc:
        raise ValueError("Invalid encrypted secret payload") from exc

    if len(payload) < 48:
        raise ValueError("Encrypted secret payload is too short")

    salt = payload[:16]
    mac = payload[16:48]
    cipher_bytes = payload[48:]

    master_key = _load_master_key()
    expected_mac = hmac.new(master_key, salt + cipher_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Secret integrity check failed")

    stream_key = _derive_stream_key(master_key, salt)
    plain = _xor_bytes(cipher_bytes, stream_key)
    try:
        return plain.decode("utf-8")
    except Exception as exc:
        raise ValueError("Decrypted secret is not valid UTF-8") from exc


def mask_secret_in_config(config: Optional[dict]) -> dict:
    if not isinstance(config, dict):
        return {}
    variables = config.get("variables", [])
    if not isinstance(variables, list):
        return dict(config)

    masked_variables = []
    for item in variables:
        if not isinstance(item, dict):
            masked_variables.append(item)
            continue
        normalized_type = str(item.get("type", "string") or "string").strip().lower()
        next_item = dict(item)
        if normalized_type == "secret":
            raw_value = next_item.get("value", "")
            if isinstance(raw_value, str) and raw_value:
                next_item["value"] = SECRET_MASK
        masked_variables.append(next_item)

    next_config = dict(config)
    next_config["variables"] = masked_variables
    return next_config
