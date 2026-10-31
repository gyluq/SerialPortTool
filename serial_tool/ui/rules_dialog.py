"""Highlight rule management dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from serial_tool.core.highlight import Rule, compile_rule


def localise_buttons(box: QDialogButtonBox) -> None:
    """Label the standard buttons in Chinese.

    Qt only translates them when a translation catalogue is loaded; without one
    the all-Chinese UI ends up with an "OK / Cancel" pair.
    """
    for role, text in ((QDialogButtonBox.Ok, "确定"), (QDialogButtonBox.Cancel, "取消")):
        button = box.button(role)
        if button is not None:
            button.setText(text)


class RuleEditDialog(QDialog):
    """Editing a single rule."""

    def __init__(self, parent=None, rule: Rule | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑规则")
        self.setMinimumWidth(360)

        self._pattern = QLineEdit(rule.pattern if rule else "")
        self._is_regex = QCheckBox("使用正则表达式")
        self._is_regex.setChecked(bool(rule and rule.is_regex))
        self._color = QColor(rule.color) if rule else QColor("#ff0000")
        self._enabled = bool(rule.enabled) if rule else True

        self._color_button = QPushButton("选择颜色")
        self._color_button.clicked.connect(self._choose_color)
        self._refresh_color_button()

        form = QFormLayout()
        form.addRow("匹配模式:", self._pattern)
        form.addRow(self._is_regex)
        form.addRow("高亮颜色:", self._color_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        localise_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(self._color, self)
        if color.isValid():
            self._color = color
            self._refresh_color_button()

    def _refresh_color_button(self) -> None:
        self._color_button.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1px solid #cccccc;"
        )
        self._color_button.setText(self._color.name())

    def result_rule(self) -> Rule | None:
        pattern = self._pattern.text().strip()
        if not pattern:
            return None
        return compile_rule(
            Rule(
                pattern=pattern,
                color=self._color.name(),
                is_regex=self._is_regex.isChecked(),
                enabled=self._enabled,
            )
        )


class RulesDialog(QDialog):
    """Managing the rule list."""

    def __init__(self, parent=None, rules: list[Rule] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("高亮规则设置")
        self.resize(600, 400)
        self._rules: list[Rule] = list(rules or [])

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["启用", "匹配模式", "类型", "颜色"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setDefaultSectionSize(25)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)

        add_button = QPushButton("添加")
        edit_button = QPushButton("编辑")
        delete_button = QPushButton("删除")
        add_button.clicked.connect(self._add_rule)
        edit_button.clicked.connect(self._edit_rule)
        delete_button.clicked.connect(self._delete_rule)

        tools = QHBoxLayout()
        tools.addWidget(add_button)
        tools.addWidget(edit_button)
        tools.addWidget(delete_button)
        tools.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        localise_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(tools)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        self._table.setRowCount(len(self._rules))
        for row, rule in enumerate(self._rules):
            checkbox = QCheckBox()
            checkbox.setChecked(rule.enabled)
            checkbox.stateChanged.connect(
                lambda state, r=rule: self._toggle(r, state == Qt.Checked.value)
            )
            self._table.setCellWidget(row, 0, checkbox)

            pattern_item = QTableWidgetItem(rule.pattern)
            pattern_item.setForeground(QColor(rule.color))
            self._table.setItem(row, 1, pattern_item)
            self._table.setItem(row, 2, QTableWidgetItem("正则" if rule.is_regex else "普通"))

            color_item = QTableWidgetItem(rule.color)
            color_item.setBackground(QColor(rule.color))
            self._table.setItem(row, 3, color_item)

    def _toggle(self, rule: Rule, enabled: bool) -> None:
        rule.enabled = enabled

    def _add_rule(self) -> None:
        dialog = RuleEditDialog(self)
        if dialog.exec() == QDialog.Accepted:
            rule = dialog.result_rule()
            if rule:
                self._rules.append(rule)
                self._refresh()

    def _edit_rule(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        dialog = RuleEditDialog(self, self._rules[row])
        if dialog.exec() == QDialog.Accepted:
            rule = dialog.result_rule()
            if rule:
                self._rules[row] = rule
                self._refresh()

    def _delete_rule(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        del self._rules[row]
        self._refresh()

    def rules(self) -> list[Rule]:
        return self._rules
