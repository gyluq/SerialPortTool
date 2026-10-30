"""Log file: naming rule and a per-line writer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

LOG_DIR_NAME = "log"


def build_log_path(base_dir: Path | str, now: datetime) -> Path:
    """The log location is decided by the base_dir passed in, not by the process CWD."""
    return Path(base_dir) / LOG_DIR_NAME / f"log_{now:%Y%m%d_%H%M%S}.log"


class LogWriter:
    """Append line by line and flush immediately, so a crash does not lose written data."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._handle = None
        self._open()

    def _open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")

    @property
    def is_open(self) -> bool:
        return self._handle is not None

    def write(self, text: str, timestamp: str | None = None) -> None:
        if self._handle is None:
            return
        prefix = f"[{timestamp}] " if timestamp else ""
        self._handle.write(prefix + text)
        self._handle.flush()

    def close(self) -> None:
        if self._handle is None:
            return
        self._handle.close()
        self._handle = None

    def __enter__(self) -> "LogWriter":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
