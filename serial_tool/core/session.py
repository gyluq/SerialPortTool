"""Serial session: port enumeration, read/write, write queue.

pyserial is imported lazily, so the core logic can be tested without hardware
and without pyserial.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Protocol

from serial_tool.core.params import SerialParams

UNKNOWN_DESCRIPTION = "未知设备"

MIN_READ_SIZE = 1024
MAX_READ_SIZE = 4096
READ_SIZE_DIVISOR = 256


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str
    hwid: str


class Transport(Protocol):
    """Serial transport abstraction, so test doubles can be injected."""

    @property
    def is_open(self) -> bool: ...

    def read(self, size: int) -> bytes: ...

    def write(self, data: bytes) -> None: ...

    def close(self) -> None: ...


def read_size_for(baudrate: int) -> int:
    """Read more per call at high baud rates to avoid many small packets slowing throughput."""
    return min(MAX_READ_SIZE, max(MIN_READ_SIZE, baudrate // READ_SIZE_DIVISOR))


def list_ports() -> list[PortInfo]:
    import serial.tools.list_ports as list_ports_module

    return [
        PortInfo(
            device=port.device,
            description=port.description or UNKNOWN_DESCRIPTION,
            hwid=port.hwid or "",
        )
        for port in list_ports_module.comports()
    ]


class PyserialTransport:
    """A real serial port. pyserial is imported only when open() is called."""

    def __init__(self, params: SerialParams) -> None:
        import serial

        self._serial = serial.Serial(
            port=params.port,
            baudrate=params.baudrate,
            bytesize=params.databits,
            parity=params.parity.value,
            stopbits=params.stopbits,
            timeout=0.01,
        )
        self._serial.inter_byte_timeout = 0.001

    @property
    def is_open(self) -> bool:
        return bool(self._serial.is_open)

    def read(self, size: int) -> bytes:
        return self._serial.read(size)

    def write(self, data: bytes) -> None:
        self._serial.write(data)

    def close(self) -> None:
        if self._serial.is_open:
            self._serial.close()


class SerialSession:
    """A single serial session.

    Every write goes into a queue first and is flushed by the worker thread via
    drain_writes(), so the GUI thread and the reader thread never touch the same
    serial object at the same time.
    """

    def __init__(
        self,
        params: SerialParams,
        transport: Transport | None = None,
    ) -> None:
        self.params = params
        self._transport = transport
        self._pending: deque[bytes] = deque()
        # An injected double may already be "open", so track constructed vs.
        # connected explicitly to avoid reads/writes before open().
        self._opened = False

    def open(self) -> "SerialSession":
        if self._transport is None:
            self._transport = PyserialTransport(self.params)
        self._opened = True
        return self

    @property
    def is_open(self) -> bool:
        return (
            self._opened
            and self._transport is not None
            and bool(self._transport.is_open)
        )

    def read_once(self, size: int | None = None) -> bytes:
        if not self.is_open:
            return b""
        assert self._transport is not None
        return self._transport.read(size or read_size_for(self.params.baudrate))

    def submit_write(self, data: bytes) -> None:
        if data:
            self._pending.append(data)

    @property
    def pending_writes(self) -> int:
        return len(self._pending)

    def drain_writes(self) -> int:
        """Write out everything in the queue and return the number of bytes written."""
        if not self.is_open or self._transport is None:
            self._pending.clear()
            return 0

        written = 0
        while self._pending:
            chunk = self._pending.popleft()
            self._transport.write(chunk)
            written += len(chunk)
        return written

    def close(self) -> None:
        self._pending.clear()
        self._opened = False
        if self._transport is not None:
            self._transport.close()

    def __enter__(self) -> "SerialSession":
        return self.open()

    def __exit__(self, *exc_info) -> None:
        self.close()
