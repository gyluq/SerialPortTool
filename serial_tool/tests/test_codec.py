import pytest

from serial_tool.core.codec import (
    HexFormatError,
    decode_text,
    encode_text,
    format_hex,
    parse_hex,
)


class TestParseHexOk:
    def test_with_spaces(self):
        assert parse_hex("AA BB") == b"\xaa\xbb"

    def test_lowercase_no_separator(self):
        assert parse_hex("aabb") == b"\xaa\xbb"

    def test_multiline(self):
        assert parse_hex("AA\nBB\r\nCC") == b"\xaa\xbb\xcc"

    def test_empty(self):
        assert parse_hex("") == b""

    def test_only_whitespace(self):
        assert parse_hex("   \n\t ") == b""

    def test_mixed_case(self):
        assert parse_hex("aA Ff") == b"\xaa\xff"


class TestParseHexErrors:
    def test_odd_length(self):
        with pytest.raises(HexFormatError) as exc:
            parse_hex("AA B")
        assert "偶数" in str(exc.value)

    def test_illegal_char(self):
        with pytest.raises(HexFormatError) as exc:
            parse_hex("ZZ")
        assert "非法" in str(exc.value)

    def test_illegal_char_inside(self):
        with pytest.raises(HexFormatError):
            parse_hex("AA?BB")

    def test_error_is_value_error(self):
        assert issubclass(HexFormatError, ValueError)


class TestFormatHex:
    def test_bytes(self):
        assert format_hex(b"\xaa\xbb") == "AA BB"

    def test_empty(self):
        assert format_hex(b"") == ""

    def test_single(self):
        assert format_hex(b"\x01") == "01"


class TestTextCodec:
    def test_decode_utf8(self):
        assert decode_text("中文".encode()) == "中文"

    def test_decode_invalid_does_not_raise(self):
        assert decode_text(b"\xff") == "\ufffd"

    def test_encode_plain(self):
        assert encode_text("A", append_newline=False) == b"A"

    def test_encode_with_newline(self):
        assert encode_text("A", append_newline=True) == b"A\r\n"

    def test_encode_chinese(self):
        assert encode_text("中", append_newline=False) == "中".encode()
