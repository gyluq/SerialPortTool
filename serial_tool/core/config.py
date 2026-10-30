"""Data model for user preferences plus tolerant deserialization.

Only handles "dict -> dataclass" here; QSettings is untouched. Storage is
adapted in the ui layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

_TRUE_WORDS = {"1", "true", "yes", "on"}
_FALSE_WORDS = {"0", "false", "no", "off", ""}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    word = str(value).strip().lower()
    if word in _TRUE_WORDS:
        return True
    if word in _FALSE_WORDS:
        return False
    raise ValueError(f"无法识别的布尔值: {value!r}")


@dataclass
class AppConfig:
    baudrate: int = 115200
    databits: int = 8
    parity: str = "N"
    stopbits: float = 1.0
    show_timestamp: bool = True
    autoscroll: bool = True
    always_on_top: bool = False
    limit_label: str = "1MB"
    hex_mode: bool = False
    append_newline: bool = False
    log_enabled: bool = False
    font_family: str = "Consolas"
    font_size: int = 10

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> "AppConfig":
        """Missing fields, wrong types or unknown keys never fail; they fall back to defaults."""
        config = cls()
        if not isinstance(data, dict):
            return config

        for field_info in fields(cls):
            if field_info.name not in data:
                continue
            default = getattr(config, field_info.name)
            raw = data[field_info.name]
            try:
                if isinstance(default, bool):
                    value: Any = _to_bool(raw)
                elif isinstance(default, int):
                    value = int(raw)
                elif isinstance(default, float):
                    value = float(raw)
                else:
                    value = str(raw)
            except (TypeError, ValueError):
                continue
            setattr(config, field_info.name, value)

        return config
