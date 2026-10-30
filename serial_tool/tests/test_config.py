from serial_tool.core.config import AppConfig


class TestDefaults:
    def test_defaults_match_requirements(self):
        cfg = AppConfig()
        assert cfg.baudrate == 115200
        assert cfg.databits == 8
        assert cfg.parity == "N"
        assert cfg.stopbits == 1.0
        assert cfg.show_timestamp is True
        assert cfg.autoscroll is True
        assert cfg.always_on_top is False
        assert cfg.limit_label == "1MB"
        assert cfg.font_family == "Consolas"
        assert cfg.font_size == 10

    def test_newly_remembered_flags(self):
        cfg = AppConfig()
        assert cfg.hex_mode is False
        assert cfg.append_newline is False
        assert cfg.log_enabled is False


class TestRoundTrip:
    def test_to_dict_round_trip(self):
        cfg = AppConfig(baudrate=9600, hex_mode=True, font_size=12)
        assert AppConfig.from_dict(cfg.to_dict()) == cfg

    def test_to_dict_has_expected_keys(self):
        keys = set(AppConfig().to_dict())
        for key in (
            "baudrate",
            "databits",
            "parity",
            "stopbits",
            "show_timestamp",
            "autoscroll",
            "always_on_top",
            "limit_label",
            "font_family",
            "font_size",
            "hex_mode",
            "append_newline",
            "log_enabled",
        ):
            assert key in keys


class TestTolerance:
    def test_empty_dict_gives_defaults(self):
        assert AppConfig.from_dict({}) == AppConfig()

    def test_bad_int_falls_back(self):
        assert AppConfig.from_dict({"baudrate": "abc"}).baudrate == 115200

    def test_none_value_falls_back(self):
        assert AppConfig.from_dict({"stopbits": None}).stopbits == 1.0

    def test_unknown_keys_ignored(self):
        assert AppConfig.from_dict({"nope": 1}) == AppConfig()

    def test_string_bool_is_coerced(self):
        assert AppConfig.from_dict({"autoscroll": "false"}).autoscroll is False

    def test_wrong_type_for_bool(self):
        assert AppConfig.from_dict({"autoscroll": 0}).autoscroll is False
