"""Application entry point.

Keeps the same launch command as before: `python main.py`.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from serial_tool.ui.main_window import SerialPortTool, apply_stylesheet

ICON_PATH = Path(__file__).resolve().parent / "icon.png"


def install_exception_hook() -> None:
    """Report errors raised inside Qt slots instead of letting them escape.

    Qt does not support exceptions crossing the C++/Python boundary: a slot that
    raises can leave the window wedged (dead modal state, no way to close it).
    Catching them here keeps the application usable and makes the failure visible.
    """

    def hook(exc_type, exc, tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        print(text, file=sys.stderr)
        QMessageBox.critical(None, "程序错误", f"{exc_type.__name__}: {exc}")

    sys.excepthook = hook


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SerialPortTool")
    app.setOrganizationName("SerialPortTool")

    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))

    apply_stylesheet(app)
    install_exception_hook()

    window = SerialPortTool()
    if ICON_PATH.exists():
        window.setWindowIcon(QIcon(str(ICON_PATH)))
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
