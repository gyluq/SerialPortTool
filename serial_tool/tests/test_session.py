import pytest

from serial_tool.core.params import Parity, SerialParams
from serial_tool.core.session import (
    PortInfo,
    SerialSession,
    list_ports,
    read_size_for,
)
from serial_tool.tests.fakes import FakeTransport


def params(**kwargs):
    base = {"port": "COM3"}
    base.update(kwargs)
    return SerialParams(**base)


class TestFakeTransport:
    def test_reads_chunks_in_order(self):
        fake = FakeTransport([b"a", b"b"])
        assert fake.read(10) == b"a"
        assert fake.read(10) == b"b"
        assert fake.read(10) == b""

    def test_records_writes(self):
        fake = FakeTransport()
        fake.write(b"x")
        assert fake.written == [b"x"]


class TestLifecycle:
    def test_open_sets_is_open(self):
        fake = FakeTransport()
        session = SerialSession(params(), transport=fake)
        session.open()
        assert session.is_open is True

    def test_close_is_idempotent(self):
        fake = FakeTransport()
        session = SerialSession(params(), transport=fake)
        session.open()
        session.close()
        session.close()
        assert session.is_open is False

    def test_read_after_close_returns_empty(self):
        fake = FakeTransport([b"data"])
        session = SerialSession(params(), transport=fake)
        session.open()
        session.close()
        assert session.read_once() == b""

    def test_read_before_open_returns_empty(self):
        session = SerialSession(params(), transport=FakeTransport([b"data"]))
        assert session.read_once() == b""


class TestReadSize:
    def test_default_baudrate_within_bounds(self):
        assert 1024 <= read_size_for(115200) <= 4096

    def test_high_baudrate_reads_more(self):
        assert read_size_for(921600) > read_size_for(115200)

    def test_low_baudrate_has_floor(self):
        assert read_size_for(9600) >= 1024

    def test_never_exceeds_cap(self):
        assert read_size_for(10_000_000) <= 4096

    def test_read_once_passes_computed_size(self):
        fake = FakeTransport()
        session = SerialSession(params(baudrate=921600), transport=fake)
        session.open()
        session.read_once()
        assert fake.last_read_size == read_size_for(921600)


class TestWriteQueue:
    def test_submit_does_not_write_immediately(self):
        fake = FakeTransport()
        session = SerialSession(params(), transport=fake)
        session.open()
        session.submit_write(b"a")
        assert fake.written == []

    def test_drain_writes_bytes(self):
        fake = FakeTransport()
        session = SerialSession(params(), transport=fake)
        session.open()
        session.submit_write(b"a")
        assert session.drain_writes() == 1
        assert fake.written == [b"a"]

    def test_multiple_submits_preserve_order(self):
        fake = FakeTransport()
        session = SerialSession(params(), transport=fake)
        session.open()
        session.submit_write(b"1")
        session.submit_write(b"2")
        assert session.drain_writes() == 2
        assert fake.written == [b"1", b"2"]

    def test_drain_without_pending(self):
        session = SerialSession(params(), transport=FakeTransport())
        session.open()
        assert session.drain_writes() == 0

    def test_drain_when_closed_returns_zero(self):
        fake = FakeTransport()
        session = SerialSession(params(), transport=fake)
        session.open()
        session.submit_write(b"a")
        session.close()
        assert session.drain_writes() == 0
        assert fake.written == []


class TestListPorts:
    def test_normalizes_description(self, monkeypatch):
        class FakePort:
            def __init__(self, device, description, hwid):
                self.device = device
                self.description = description
                self.hwid = hwid

        import serial.tools.list_ports as list_ports_module

        monkeypatch.setattr(
            list_ports_module,
            "comports",
            lambda: [
                FakePort("COM1", "USB-SERIAL CH340", "USB VID:PID=1A86:7523"),
                FakePort("COM2", None, None),
            ],
        )

        ports = list_ports()
        assert ports == [
            PortInfo("COM1", "USB-SERIAL CH340", "USB VID:PID=1A86:7523"),
            PortInfo("COM2", "未知设备", ""),
        ]

    def test_empty(self, monkeypatch):
        import serial.tools.list_ports as list_ports_module

        monkeypatch.setattr(list_ports_module, "comports", lambda: [])
        assert list_ports() == []
