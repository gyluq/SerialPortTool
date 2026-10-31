"""Data model for user preferences plus tolerant deserialization.

Only handles "dict -> dataclass" here; QSettings is untouched. Storage is
adapted in the ui layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

_TRUE_WORDS = {"1", "true", "yes", "on"}
_FALSE_WORDS = {"0", "false", "no", "off", ""}


def app_base_dir(is_frozen: bool, executable: Path | str, package_file: Path | str) -> Path:
    """Directory that should hold files meant to outlive the process, such as logs.

    A onefile PyInstaller build unpacks the package into a temporary directory
    (``_MEIxxxx``) and deletes it on exit, so ``__file__`` is useless there: it
    would put logs somewhere the user can never open. When frozen, the anchor
    is the executable instead.

    Callers pass ``sys.frozen``, ``sys.executable`` and ``__file__`` rather than
    reading them here, so the rule stays a pure function and stays testable.
    """
    if is_frozen:
        return Path(executable).resolve().parent
    return Path(package_file).resolve().parents[2]


def resource_dir(is_frozen: bool, bundle_dir: str | None, package_file: Path | str) -> Path:
    """Directory holding read-only assets shipped with the app (icon, data files).

    This is a different question from app_base_dir: bundled assets do live
    inside the temporary unpack dir, so when frozen it is the right answer.
    Keeping the two rules apart stops one being used for the other by accident.
    """
    if is_frozen and bundle_dir:
        return Path(bundle_dir)
    return Path(package_file).resolve().parent


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
