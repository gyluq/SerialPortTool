"""Console visibility rule.

Pure logic, no Qt: the window decides whether the bottom console is shown
from its width and from the user's manual choice.
"""

from __future__ import annotations

from serial_tool.core.layout import CONSOLE_BREAKPOINT, console_visible


class TestAutoMode:
    def test_wide_window_shows_console(self):
        assert console_visible(CONSOLE_BREAKPOINT + 20, None) is True

    def test_narrow_window_hides_console(self):
        assert console_visible(CONSOLE_BREAKPOINT - 400, None) is False

    def test_breakpoint_is_inclusive(self):
        assert console_visible(CONSOLE_BREAKPOINT, None) is True
        assert console_visible(CONSOLE_BREAKPOINT - 1, None) is False


class TestManualMode:
    def test_manual_hide_wins_on_a_wide_window(self):
        assert console_visible(1280, False) is False

    def test_manual_show_wins_on_a_narrow_window(self):
        assert console_visible(800, True) is True
