"""Window layout decisions that do not need Qt.

The bottom console (port settings and controls) needs about 1182 px to fit.
Keeping that rule here lets it be tested without a display.
"""

from __future__ import annotations

# Width below which the console no longer fits, so it collapses to a compact bar.
# The console itself needs about 1275 px plus window margins, so the breakpoint
# sits just above that: the console is never shown while it would overflow.
CONSOLE_BREAKPOINT = 1300

# The window may shrink well below the console width: at that point the console
# is either hidden or, if the user forced it open, shown behind a scroll area.
MIN_WINDOW_WIDTH = 520
MIN_WINDOW_HEIGHT = 420


def console_visible(window_width: int, manual: bool | None) -> bool:
    """Whether the bottom console should be visible.

    manual is the user's explicit choice: True to keep it open, False to keep it
    closed, None to let the width decide. A manual choice always wins, so the
    automatic rule never fights the user.
    """
    if manual is not None:
        return manual
    return window_width >= CONSOLE_BREAKPOINT
