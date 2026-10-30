"""Wire the core matching engine into Qt's highlighting mechanism.

The matching logic itself lives in core.highlight; this class only paints the ranges.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from serial_tool.core.highlight import Rule, find_matches


class RuleHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument, rules: list[Rule] | None = None) -> None:
        super().__init__(document)
        self._rules: list[Rule] = rules or []

    @property
    def rules(self) -> list[Rule]:
        return self._rules

    def set_rules(self, rules: list[Rule]) -> None:
        self._rules = rules
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt naming)
        for start, end, color in find_matches(text, self._rules):
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(color))
            char_format.setFontWeight(QFont.Bold)
            self.setFormat(start, end - start, char_format)
