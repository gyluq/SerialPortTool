import pytest

from serial_tool.core.params import (
    BAUD_CHOICES,
    DATABITS_CHOICES,
    PARITY_LABELS,
    STOPBITS_CHOICES,
    STOPBITS_LABELS,
    Parity,
    SerialParams,
    validate,
)


class TestDefaults:
    def test_default_values(self):
        p = SerialParams(port="COM3")
        assert p.port == "COM3"
        assert p.baudrate == 115200
        assert p.databits == 8
        assert p.parity == Parity.NONE
        assert p.stopbits == 1.0

    def test_baud_choices_sorted_and_contains_default(self):
        assert 115200 in BAUD_CHOICES
        assert list(BAUD_CHOICES) == sorted(BAUD_CHOICES)

    def test_databits_choices(self):
        assert DATABITS_CHOICES == (5, 6, 7, 8)

    def test_stopbits_choices(self):
        assert STOPBITS_CHOICES == (1.0, 1.5, 2.0)


class TestLabels:
    def test_parity_labels_map_to_enum(self):
        assert PARITY_LABELS["无"] is Parity.NONE
        assert PARITY_LABELS["偶"] is Parity.EVEN
        assert PARITY_LABELS["奇"] is Parity.ODD
        assert PARITY_LABELS["Mark"] is Parity.MARK
        assert PARITY_LABELS["Space"] is Parity.SPACE

    def test_stopbits_labels(self):
        assert STOPBITS_LABELS[1.0] == "1"
        assert STOPBITS_LABELS[1.5] == "1.5"
        assert STOPBITS_LABELS[2.0] == "2"


class TestValidate:
    def test_empty_port(self):
        assert validate(SerialParams(port="")) == ["请选择串口"]

    def test_valid_params(self):
        assert validate(SerialParams(port="COM3")) == []

    def test_zero_baudrate(self):
        errors = validate(SerialParams(port="COM3", baudrate=0))
        assert any("波特率" in e for e in errors)

    def test_negative_baudrate(self):
        errors = validate(SerialParams(port="COM3", baudrate=-1))
        assert any("波特率" in e for e in errors)

    def test_invalid_databits(self):
        errors = validate(SerialParams(port="COM3", databits=9))
        assert any("数据位" in e for e in errors)

    @pytest.mark.parametrize("stopbits", STOPBITS_CHOICES)
    def test_all_stopbits_legal(self, stopbits):
        assert validate(SerialParams(port="COM3", stopbits=stopbits)) == []
