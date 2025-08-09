"""
样式模块 - 包含应用程序的所有样式定义

此模块提供了统一的应用程序样式管理，便于维护和修改。
"""

# 应用程序样式表
APP_STYLESHEET = """
QMainWindow {
    background-color: #f5f5f5;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #cccccc;
    border-radius: 6px;
    margin-top: 1ex;
    padding-top: 8px;
    background-color: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #333333;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 3px 8px;
    color: #333333;
    font-weight: normal;
    min-height: 16px;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #f8f9fa;
    border-color: #adb5bd;
}
QPushButton:pressed {
    background-color: #e9ecef;
    border-color: #adb5bd;
}
QPushButton:disabled {
    background-color: #f8f9fa;
    color: #6c757d;
    border-color: #dee2e6;
}
QComboBox {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 2px 6px;
    min-height: 16px;
    font-size: 11px;
}
QComboBox:hover {
    border-color: #adb5bd;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border: none;
}
QComboBox QAbstractItemView {
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: white;
    outline: 0px;
    color: #333333;
    selection-background-color: #007bff;
    selection-color: white;
}
QComboBox QAbstractItemView::item {
    padding: 6px 12px;
}
QLineEdit {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 0px 4px;
    min-height: 24px;
}
QLineEdit:focus {
    border-color: #007bff;
    outline: none;
}
QTextEdit {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px;
}
QTextEdit:focus {
    border-color: #007bff;
}
QCheckBox {
    color: #333333;
}
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                               stop:0 #f8f9fa, stop:1 #e9ecef);
    border-bottom: 2px solid #dee2e6;
    color: #495057;
    font-weight: 500;
    font-size: 11px;
    min-height: 20px;
    padding: 1px 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 2px 8px;
    border-radius: 3px;
    margin: 1px;
}

QMenuBar::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                               stop:0 #007bff, stop:1 #0056b3);
    color: white;
}

QMenuBar::item:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                               stop:0 #0056b3, stop:1 #004085);
    color: white;
}

QMenu {
    background-color: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 2px;
    font-size: 11px;
}

QMenu::item {
    padding: 3px 16px 3px 16px;
    border-radius: 3px;
    margin: 1px;
}

QMenu::item:selected {
    background-color: #007bff;
    color: white;
}

QMenu::separator {
    height: 1px;
    background: #dee2e6;
    margin: 4px 8px;
}

QMenu::indicator {
    width: 12px;
    height: 12px;
    border: 1px solid #cccccc;
    border-radius: 2px;
    background-color: white;
}

QMenu::indicator:checked {
    background-color: #007bff;
    border-color: #007bff;
}
"""


def get_application_stylesheet():
    """获取应用程序样式表"""
    return APP_STYLESHEET


def apply_stylesheet(app):
    """应用样式表到应用程序"""
    app.setStyleSheet(get_application_stylesheet())