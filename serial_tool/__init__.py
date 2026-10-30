"""SerialPortTool - serial port debugging tool built with PySide6.

Layering:
    serial_tool.core  pure logic, no Qt dependency, testable on its own
    serial_tool.ui    thin PySide6 shell
"""

__version__ = "2.0.0"
__all__ = ["__version__"]
