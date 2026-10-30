"""Shared fixtures for UI tests.

Works without pytest-qt: we manage a QApplication ourselves and point
QSettings at a temporary ini file so the real local config is never touched.
"""

from __future__ import annotations

import os

import pytest

# Must be set before importing PySide6, otherwise a headless environment fails outright
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="UI 测试需要 PySide6")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    from serial_tool.ui.main_window import apply_stylesheet

    app = QApplication.instance() or QApplication([])
    # Apply the real stylesheet: a rule with font-size would silently override
    # setFont, and tests must see that, not a bare widget.
    apply_stylesheet(app)
    yield app


@pytest.fixture
def store(qapp, tmp_path):
    from serial_tool.ui.settings_store import SettingsStore

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.clear()
    return SettingsStore(settings)


@pytest.fixture
def window(qapp, store):
    from serial_tool.ui.main_window import SerialPortTool

    win = SerialPortTool(store=store)
    yield win
    win.close()


@pytest.fixture
def connected(window):
    """Attach the main window to a fake serial port; returns (window, fake_transport)."""
    from serial_tool.tests.fakes import FakeTransport

    fake = FakeTransport()
    window._transport_factory = lambda params: fake
    window.port_combo.addItem("COM3", "COM3")
    window.port_combo.setCurrentIndex(window.port_combo.count() - 1)
    window._connect()
    return window, fake
