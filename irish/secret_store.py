"""Encrypt and load API credentials using the current Windows user's DPAPI key."""

import base64
import ctypes
import json
import os
import re
from ctypes import wintypes
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
ENV_PATH = PROJECT_DIR / ".env"
STORE_PATH = PROJECT_DIR / ".secrets.dpapi.json"
SECRET_NAMES = {
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
}


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data):
    buffer = ctypes.create_string_buffer(data, len(data))
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _dpapi(data, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Protected API keys can only be read on Windows.")

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    source, source_buffer = _blob(data)
    result = _DataBlob()

    if decrypt:
        operation = crypt32.CryptUnprotectData
        operation.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR),
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        operation.restype = wintypes.BOOL
        ok = operation(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result))
    else:
        operation = crypt32.CryptProtectData
        operation.argtypes = [
            ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        operation.restype = wintypes.BOOL
        ok = operation(ctypes.byref(source), "Irish API credential", None, None, None, 1, ctypes.byref(result))

    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(result.pbData)


def _protect_secret(value):
    encrypted = _dpapi(value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("ascii")


def _unprotect_secret(value):
    encrypted = base64.b64decode(value, validate=True)
    return _dpapi(encrypted, decrypt=True).decode("utf-8")


def encrypt_env_secrets():
    """Move supported API keys from plaintext .env into a DPAPI-protected store."""
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"No .env file found at {ENV_PATH}")

    original = ENV_PATH.read_text(encoding="utf-8")
    existing = json.loads(STORE_PATH.read_text(encoding="utf-8")) if STORE_PATH.exists() else {}
    protected = dict(existing)
    remaining_lines = []
    migrated = []

    for line in original.splitlines(keepends=True):
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*(?:\r?\n)?$", line)
        if not match or match.group(1) not in SECRET_NAMES:
            remaining_lines.append(line)
            continue

        name, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not value:
            remaining_lines.append(line)
            continue

        protected[name] = _protect_secret(value)
        migrated.append(name)

    if not migrated:
        return []

    temp_store = STORE_PATH.with_suffix(STORE_PATH.suffix + ".tmp")
    temp_env = ENV_PATH.with_suffix(ENV_PATH.suffix + ".tmp")
    temp_store.write_text(json.dumps(protected, indent=2) + "\n", encoding="utf-8")
    temp_env.write_text("".join(remaining_lines), encoding="utf-8")
    os.replace(temp_store, STORE_PATH)
    os.replace(temp_env, ENV_PATH)
    return migrated


def load_protected_secrets():
    """Load decrypted credentials into the process environment when available."""
    if not STORE_PATH.exists():
        return

    protected = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    for name, value in protected.items():
        if name in SECRET_NAMES and name not in os.environ:
            os.environ[name] = _unprotect_secret(value)
