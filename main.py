"""Application entry point.

Keeps the same launch command as before: `python main.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from serial_tool.ui.main_window import SerialPortTool, apply_stylesheet

ICON_PATH = Path(__file__).resolve().parent / "icon.png"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SerialPortTool")
    app.setOrganizationName("SerialPortTool")

    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))

    apply_stylesheet(app)

    window = SerialPortTool()
    if ICON_PATH.exists():
        window.setWindowIcon(QIcon(str(ICON_PATH)))
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
