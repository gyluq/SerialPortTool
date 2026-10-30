"""Adapter between QSettings and AppConfig / highlight rules."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings

from serial_tool.core.config import AppConfig
from serial_tool.core.highlight import Rule, compile_rule

CONFIG_KEY = "config"
RULES_KEY = "rules"


class SettingsStore:
    """Config persistence is isolated here; the main window never touches QSettings directly."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings("SerialPortTool", "MainApp")

    def load_config(self) -> AppConfig:
        raw = self._settings.value(CONFIG_KEY, {})
        if not isinstance(raw, dict):
            return AppConfig()
        return AppConfig.from_dict({str(k): v for k, v in raw.items()})

    def save_config(self, config: AppConfig) -> None:
        self._settings.setValue(CONFIG_KEY, config.to_dict())
        self._settings.sync()

    def load_rules(self) -> list[Rule]:
        raw = self._settings.value(RULES_KEY, [])
        rules: list[Rule] = []
        if not isinstance(raw, list):
            return rules

        for item in raw:
            if not isinstance(item, dict):
                continue
            pattern = str(item.get("pattern", ""))
            if not pattern:
                continue
            rules.append(
                compile_rule(
                    Rule(
                        pattern=pattern,
                        color=str(item.get("color", "#ff0000")),
                        is_regex=bool(item.get("is_regex", False)),
                        enabled=bool(item.get("enabled", True)),
                    )
                )
            )
        return rules

    def save_rules(self, rules: list[Rule]) -> None:
        payload: list[dict[str, Any]] = [
            {
                "pattern": rule.pattern,
                "color": rule.color,
                "is_regex": rule.is_regex,
                "enabled": rule.enabled,
            }
            for rule in rules
        ]
        self._settings.setValue(RULES_KEY, payload)
        self._settings.sync()
