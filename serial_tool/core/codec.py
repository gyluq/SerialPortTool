"""Hex and text encoding/decoding.

All parse errors raise HexFormatError, carrying a user-facing reason.
"""

from __future__ import annotations

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class HexFormatError(ValueError):
    """The hex input is invalid."""


def parse_hex(text: str) -> bytes:
    """Convert the hex string typed by the user into bytes.

    Any whitespace (spaces, newlines, tabs) is tolerated, other characters are not.
    """
    cleaned = "".join(text.split())
    if not cleaned:
        return b""

    for char in cleaned:
        if char not in _HEX_DIGITS:
            raise HexFormatError(f"十六进制数据包含非法字符: {char}")

    if len(cleaned) % 2 != 0:
        raise HexFormatError("十六进制数据长度必须为偶数")

    return bytes.fromhex(cleaned)


def format_hex(data: bytes) -> str:
    """Format bytes as "AA BB", used for echo back to the user."""
    return " ".join(f"{byte:02X}" for byte in data)


def decode_text(data: bytes) -> str:
    """Decode as UTF-8, replacing invalid bytes with U+FFFD instead of raising."""
    return data.decode("utf-8", errors="replace")


def encode_text(text: str, append_newline: bool = False) -> bytes:
    """Encode text into bytes, optionally appending CRLF."""
    payload = text.encode("utf-8")
    if append_newline:
        payload += b"\r\n"
    return payload
