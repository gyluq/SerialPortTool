"""Global stylesheets. Visuals keep the original palette: light panels, dark display area."""

from __future__ import annotations

DISPLAY_STYLE = """
QTextBrowser {
    background-color: #1e1e1e;
    color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 4px;
}
"""

APP_STYLESHEET = """
QMainWindow { background-color: #f5f5f5; }
QGroupBox {
    font-weight: bold;
    border: 1px solid #cccccc;
    border-radius: 6px;
    margin-top: 1ex;
    padding-top: 8px;
    background-color: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #333333;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 3px 8px;
    color: #333333;
    min-height: 16px;
    font-size: 11px;
}
QPushButton:hover { background-color: #f8f9fa; border-color: #adb5bd; }
QPushButton:pressed { background-color: #e9ecef; border-color: #adb5bd; }
QPushButton:disabled { background-color: #f8f9fa; color: #6c757d; border-color: #dee2e6; }
QComboBox, QLineEdit, QTextEdit {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
}
QComboBox:hover, QLineEdit:hover { border-color: #adb5bd; }
QLineEdit:focus, QTextEdit:focus { border-color: #007bff; }
QCheckBox { color: #333333; }
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);
    border-bottom: 2px solid #dee2e6;
    color: #495057;
    font-size: 11px;
    min-height: 20px;
    padding: 1px 4px;
}
QMenuBar::item { background: transparent; padding: 2px 8px; border-radius: 3px; margin: 1px; }
QMenuBar::item:selected { background-color: #007bff; color: white; }
QMenu { background-color: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 2px; font-size: 11px; }
QMenu::item { padding: 3px 16px 3px 16px; border-radius: 3px; margin: 1px; }
QMenu::item:selected { background-color: #007bff; color: white; }
QMenu::separator { height: 1px; background: #dee2e6; margin: 4px 8px; }
QStatusBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);
    border-top: 2px solid #dee2e6;
    color: #495057;
    font-size: 10px;
}
QStatusBar::item { border: none; }
"""

CONNECT_BUTTON_CONNECTED = """
QPushButton {
    background-color: #008BD3;
    border: 1px solid #adadad;
    border-radius: 3px;
    color: white;
}
QPushButton:hover { background-color: #0885c4; }
QPushButton:pressed { background-color: #0c7fb9; }
"""

CONNECT_BUTTON_IDLE = """
QPushButton {
    background-color: #eeeeee;
    border: 1px solid #adadad;
    border-radius: 3px;
    color: black;
}
QPushButton:hover { background-color: #e1e1e1; }
QPushButton:pressed { background-color: #cdcdcd; }
"""

PAUSE_BUTTON_ACTIVE = "QPushButton { background-color: #ff9800; color: white; }"
