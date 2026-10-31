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


def _line_fragment(line: Line) -> str:
    """Colored body of one line, without any line break of its own."""
    parts: list[str] = []

    if line.timestamp:
        parts.append(
            f'<span style="color:{TIMESTAMP_COLOR};">'
            f"[{html.escape(line.timestamp, quote=False)}]</span> "
        )

    color = STYLE_COLORS.get(line.style, STYLE_COLORS[Style.RECEIVED])
    parts.append(f'<span style="color:{color};">{_escape(line.text)}</span>')

    return "".join(parts)


def render_line_html(line: Line) -> str:
    """Render one line terminated by <br>, for callers that own the line break."""
    return _line_fragment(line) + "<br>"


def render_paragraph_html(line: Line) -> str:
    """Render one line without a trailing <br>.

    QTextEdit.append() already starts a new block, so appending a <br> would
    leave an empty line between every message. This is the streaming path: it
    costs O(1) per line, unlike inserting into a cursor at the document end.
    """
    return _line_fragment(line)
