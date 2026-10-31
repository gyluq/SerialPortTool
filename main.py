"""Application entry point.

Keeps the same launch command as before: `python main.py`.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from serial_tool.core.config import resource_dir
from serial_tool.ui.main_window import SerialPortTool, apply_stylesheet

# Bundled assets are unpacked into the temporary _MEIPASS directory in a
# packaged build, which is not the same place as the log directory.
ASSET_DIR = resource_dir(
    is_frozen=bool(getattr(sys, "frozen", False)),
    bundle_dir=getattr(sys, "_MEIPASS", None),
    package_file=__file__,
)


def load_icon(base: Path | None = None) -> QIcon | None:
    """Prefer the multi-resolution .ico so Windows can pick an exact frame.

    A single large PNG gets resampled for the 16 px title bar and the taskbar,
    which blurs; the .ico carries purpose-drawn frames for every size.
    """
    directory = base or ASSET_DIR
    for name in ("icon.ico", "icon.png"):
        path = directory / name
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return None


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

    if icon := load_icon():
        app.setWindowIcon(icon)

    apply_stylesheet(app)
    install_exception_hook()

    window = SerialPortTool()
    if icon := load_icon():
        window.setWindowIcon(icon)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
