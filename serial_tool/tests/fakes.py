"""Test doubles: let the serial logic be verified without hardware or pyserial."""

from __future__ import annotations

from collections import deque


class FakeTransport:
    """Minimal double implementing the Transport protocol."""

    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self._chunks: deque[bytes] = deque(chunks or [])
        self.written: list[bytes] = []
        self.close_count = 0
        self._open = True

    @property
    def is_open(self) -> bool:
        return self._open

    def read(self, size: int) -> bytes:
        self.last_read_size = size
        if not self._chunks:
            return b""
        return self._chunks.popleft()

    def write(self, data: bytes) -> None:
        self.written.append(data)

    def close(self) -> None:
        self._open = False
        self.close_count += 1

    def feed(self, data: bytes) -> None:
        self._chunks.append(data)
