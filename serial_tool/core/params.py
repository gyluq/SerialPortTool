"""Serial port connection parameters: allowed values, label mappings, validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Parity(str, Enum):
    """Parity. The value maps directly to pyserial's single-letter argument."""

    NONE = "N"
    EVEN = "E"
    ODD = "O"
    MARK = "M"
    SPACE = "S"


BAUD_CHOICES: tuple[int, ...] = (
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
    921600,
)
DATABITS_CHOICES: tuple[int, ...] = (5, 6, 7, 8)
STOPBITS_CHOICES: tuple[float, ...] = (1.0, 1.5, 2.0)

PARITY_LABELS: dict[str, Parity] = {
    "无": Parity.NONE,
    "偶": Parity.EVEN,
    "奇": Parity.ODD,
    "Mark": Parity.MARK,
    "Space": Parity.SPACE,
}
PARITY_REVERSE_LABELS: dict[Parity, str] = {v: k for k, v in PARITY_LABELS.items()}

STOPBITS_LABELS: dict[float, str] = {1.0: "1", 1.5: "1.5", 2.0: "2"}
STOPBITS_REVERSE_LABELS: dict[str, float] = {v: k for k, v in STOPBITS_LABELS.items()}


@dataclass(frozen=True)
class SerialParams:
    port: str
    baudrate: int = 115200
    databits: int = 8
    parity: Parity = Parity.NONE
    stopbits: float = 1.0


def validate(params: SerialParams) -> list[str]:
    """Return a list of error messages; an empty list means the params are usable."""
    errors: list[str] = []
    if not params.port:
        errors.append("请选择串口")
    if params.baudrate <= 0:
        errors.append("波特率必须为正整数")
    if params.databits not in DATABITS_CHOICES:
        errors.append("数据位必须是 5 / 6 / 7 / 8")
    if params.stopbits not in STOPBITS_CHOICES:
        errors.append("停止位必须是 1 / 1.5 / 2")
    return errors
