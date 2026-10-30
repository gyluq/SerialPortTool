"""Render a single line into an HTML fragment that can be inserted into QTextBrowser.

This is the **only HTML escaping point** in the project: anything coming from
the serial port must go through html.escape, otherwise device output such as
<b> would be interpreted as markup.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from enum import Enum

TIMESTAMP_COLOR = "#888888"


class Style(str, Enum):
    """Message origin, which determines the body text color."""

    SYSTEM = "system"
    SENT = "sent"
    RECEIVED = "received"


STYLE_COLORS: dict[Style, str] = {
    Style.SYSTEM: "#888888",
    Style.SENT: "#008000",
    Style.RECEIVED: "#e6e6e6",
}


@dataclass(frozen=True)
class Line:
    """A single line to display. timestamp is formatted by the caller; no time math here."""

    text: str
    style: Style = Style.RECEIVED
    timestamp: str | None = None


def _escape(text: str) -> str:
    """Escape, then turn internal newlines into <br> to avoid extra blank lines."""
    escaped = html.escape(text, quote=False)
    return escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def render_line_html(line: Line) -> str:
    """Render one line. The fragment ends with exactly one <br>."""
    parts: list[str] = []

    if line.timestamp:
        parts.append(
            f'<span style="color:{TIMESTAMP_COLOR};">'
            f"[{html.escape(line.timestamp, quote=False)}]</span> "
        )

    color = STYLE_COLORS.get(line.style, STYLE_COLORS[Style.RECEIVED])
    parts.append(f'<span style="color:{color};">{_escape(line.text)}</span>')
    parts.append("<br>")

    return "".join(parts)
