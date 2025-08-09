import re
from typing import List
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout,
    QPushButton,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QColorDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStyledItemDelegate,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QTextCharFormat,
    QSyntaxHighlighter,
    QTextDocument,
)
from PySide6.QtCore import Qt


class HighlightRule:
    def __init__(self, pattern: str, color: QColor, is_regex: bool = False, enabled: bool = True):
        self.pattern = pattern
        self.color = color
        self.is_regex = is_regex
        self.enabled = enabled
        self.regex = None
        if is_regex:
            try:
                self.regex = re.compile(pattern)
            except re.error:
                self.regex = None


class HighlightRulesDialog(QDialog):
    def __init__(self, parent=None, rules=None):
        super().__init__(parent)
        self.setWindowTitle("高亮规则设置")
        self.setGeometry(200, 200, 600, 400)
        self.rules = rules or []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(4)
        self.rules_table.setHorizontalHeaderLabels(["启用", "匹配模式", "类型", "颜色"])
        self.rules_table.horizontalHeader().setStretchLastSection(True)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rules_table.setSelectionMode(QTableWidget.NoSelection)
        # 设置除第一列外的所有列不可编辑
        self.rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 设置更紧凑的行高
        self.rules_table.verticalHeader().setDefaultSectionSize(25)
        self.rules_table.verticalHeader().setMinimumSectionSize(20)
        layout.addWidget(self.rules_table)

        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.edit_btn = QPushButton("编辑")
        self.delete_btn = QPushButton("删除")
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.add_btn.clicked.connect(self.add_rule)
        self.edit_btn.clicked.connect(self.edit_rule)
        self.delete_btn.clicked.connect(self.delete_rule)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self.update_rules_list()

    def on_checkbox_changed(self, state):
        # 获取发送信号的checkbox
        checkbox = self.sender()
        if checkbox:
            # 找到checkbox所在的行
            for i in range(self.rules_table.rowCount()):
                if self.rules_table.cellWidget(i, 0) == checkbox:
                    rule = self.rules[i]
                    rule.enabled = (state == Qt.Checked.value)
                    break

    def update_rules_list(self):
        self.rules_table.setRowCount(len(self.rules))
        for i, rule in enumerate(self.rules):
            # 启用状态checkbox
            checkbox_widget = QCheckBox()
            checkbox_widget.setChecked(rule.enabled)
            checkbox_widget.stateChanged.connect(self.on_checkbox_changed)
            self.rules_table.setCellWidget(i, 0, checkbox_widget)
            
            # 匹配模式
            pattern_item = QTableWidgetItem(rule.pattern)
            pattern_item.setForeground(rule.color)
            self.rules_table.setItem(i, 1, pattern_item)
            
            # 类型
            type_item = QTableWidgetItem("正则" if rule.is_regex else "普通")
            self.rules_table.setItem(i, 2, type_item)
            
            # 颜色
            color_item = QTableWidgetItem(rule.color.name())
            color_item.setBackground(rule.color)
            self.rules_table.setItem(i, 3, color_item)

    def add_rule(self):
        dialog = RuleEditDialog(self)
        if dialog.exec() == QDialog.Accepted:
            rule = dialog.get_rule()
            if rule:
                self.rules.append(rule)
                self.update_rules_list()

    def edit_rule(self):
        current_row = self.rules_table.currentRow()
        if current_row >= 0:
            rule = self.rules[current_row]
            dialog = RuleEditDialog(self, rule)
            if dialog.exec() == QDialog.Accepted:
                new_rule = dialog.get_rule()
                if new_rule:
                    # 保持原有的启用状态
                    new_rule.enabled = rule.enabled
                    self.rules[current_row] = new_rule
                    self.update_rules_list()

    def delete_rule(self):
        current_row = self.rules_table.currentRow()
        if current_row >= 0:
            del self.rules[current_row]
            self.update_rules_list()

    def get_rules(self):
        return self.rules


class RuleEditDialog(QDialog):
    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self.setWindowTitle("编辑规则")
        self.setGeometry(300, 300, 400, 200)
        self.rule = rule
        self.color = QColor(255, 0, 0) if not rule else rule.color
        self.init_ui()

        if rule:
            self.pattern_edit.setText(rule.pattern)
            self.regex_cb.setChecked(rule.is_regex)
            self.color = rule.color
            self.update_color_button()

    def init_ui(self):
        layout = QFormLayout(self)

        self.pattern_edit = QLineEdit()
        layout.addRow("匹配模式:", self.pattern_edit)

        self.regex_cb = QCheckBox("使用正则表达式")
        layout.addRow(self.regex_cb)

        self.color_btn = QPushButton("选择颜色")
        self.color_btn.clicked.connect(self.choose_color)
        layout.addRow("高亮颜色:", self.color_btn)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addRow(button_layout)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self.update_color_button()

    def choose_color(self):
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self.update_color_button()

    def update_color_button(self):
        self.color_btn.setStyleSheet(f"background-color: {self.color.name()}")

    def get_rule(self):
        pattern = self.pattern_edit.text().strip()
        if not pattern:
            return None
        # 如果是新建规则，默认启用；如果是编辑规则，保持原有启用状态
        enabled = getattr(self.rule, 'enabled', True) if self.rule else True
        return HighlightRule(pattern, self.color, self.regex_cb.isChecked(), enabled)


class TextHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument, rules: List[HighlightRule]):
        super().__init__(document)
        self.rules = rules

    def highlightBlock(self, text: str):
        for rule in self.rules:
            # 只处理启用的规则
            if not rule.enabled:
                continue
                
            format = QTextCharFormat()
            format.setForeground(rule.color)
            format.setFontWeight(QFont.Bold)

            if rule.is_regex and rule.regex:
                matches = rule.regex.finditer(text)
                for match in matches:
                    self.setFormat(match.start(), match.end() - match.start(), format)
            else:
                # 简单字符串匹配
                index = text.find(rule.pattern)
                while index >= 0:
                    length = len(rule.pattern)
                    self.setFormat(index, length, format)
                    index = text.find(rule.pattern, index + length)

    def update_rules(self, rules: List[HighlightRule]):
        self.rules = rules
        self.rehighlight()
