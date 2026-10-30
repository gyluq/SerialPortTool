"""Character counters for received and sent data in a session."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Counter:
    received: int = 0
    sent: int = 0

    def add_received(self, count: int) -> None:
        if count > 0:
            self.received += count

    def add_sent(self, count: int) -> None:
        if count > 0:
            self.sent += count

    def reset(self) -> None:
        self.received = 0
        self.sent = 0

    def text(self) -> str:
        return f"接收: {self.received} 字符  |  发送: {self.sent} 字符"
