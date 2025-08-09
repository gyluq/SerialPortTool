import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QComboBox,
    QPushButton,
    QTextEdit,
    QLabel,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QLineEdit,
    QSplitter,
    QTextBrowser,
    QMessageBox,
    QDialog,
    QColorDialog,
    QFontDialog,
    QFrame,
    QStatusBar,
    QMenuBar,
    QMenu,
    QSizePolicy,
    QSpacerItem,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings
from PySide6.QtGui import (
    QFont,
    QTextCharFormat,
    QColor,
    QTextCursor,
    QSyntaxHighlighter,
    QTextDocument,
    QAction,
)

import serial
import serial.tools.list_ports
from modules.threads import SerialPortMonitor, SerialWorker
from modules.highlighting import (
    HighlightRule,
    HighlightRulesDialog,
    RuleEditDialog,
    TextHighlighter,
)


class SerialPortTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("SerialPortTool", "MainApp")
        self.serial_worker: Optional[SerialWorker] = None
        self.port_monitor = SerialPortMonitor()
        self.is_connected = False
        self.is_paused = False
        self.log_file: Optional[str] = None
        self.highlight_rules: List[HighlightRule] = []
        self.highlighter: Optional[TextHighlighter] = None
        
        # 添加计数器
        self.received_count = 0
        self.sent_count = 0

        self.init_ui()
        self.init_connections()
        self.load_settings()

        self.port_monitor.start()

    def init_ui(self):
        self.setWindowTitle("串口工具")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(2)
        splitter.setChildrenCollapsible(False)
        
        self.data_display = QTextBrowser()
        self.data_display.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.highlighter = TextHighlighter(
            self.data_display.document(), self.highlight_rules
        )
        
        # 控制面板（包含连接设置、发送区域、控制选项）
        control_panel = self.create_control_panel()
        control_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        splitter.addWidget(self.data_display)
        splitter.addWidget(control_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        
        main_layout.addWidget(splitter, stretch=1)
        
        self.create_status_bar()
        self.create_menu_bar()

    def create_control_panel(self):
        """创建控制面板，左右分栏布局"""
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(6, 6, 6, 6)
        control_layout.setSpacing(8)

        left_panel = self.create_connection_panel()
        control_layout.addWidget(left_panel)

        right_panel = self.create_right_panel()
        control_layout.addWidget(right_panel)

        return control_widget

    def create_connection_panel(self):
        """创建左侧连接设置面板"""
        group = QGroupBox("串口连接")
        layout = QGridLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        port_label = QLabel("端口:")
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        
        baudrate_label = QLabel("波特率:")
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.setMinimumWidth(80)
        baudrates = [
            "9600", "19200", "38400", "57600", "115200",
            "230400", "460800", "921600",
        ]
        self.baudrate_combo.addItems(baudrates)
        self.baudrate_combo.setCurrentText("115200")
        
        layout.addWidget(port_label, 0, 0)
        layout.addWidget(self.port_combo, 0, 1)
        layout.addWidget(baudrate_label, 0, 2)
        layout.addWidget(self.baudrate_combo, 0, 3)

        databits_label = QLabel("数据位:")
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(["5", "6", "7", "8"])
        self.databits_combo.setCurrentText("8")
        
        parity_label = QLabel("校验位:")
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        
        layout.addWidget(databits_label, 1, 0)
        layout.addWidget(self.databits_combo, 1, 1)
        layout.addWidget(parity_label, 1, 2)
        layout.addWidget(self.parity_combo, 1, 3)

        stopbits_label = QLabel("停止位:")
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "1.5", "2"])
        
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setMinimumWidth(80)
        
        layout.addWidget(stopbits_label, 2, 0)
        layout.addWidget(self.stopbits_combo, 2, 1)
        layout.addWidget(self.connect_btn, 2, 2, 1, 2)

        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 3, 0, 1, 4)

        return group

    def create_right_panel(self):
        """创建右侧面板，包含发送区域和控制选项"""
        right_group = QGroupBox("功能控制")
        right_layout = QVBoxLayout(right_group)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        top_controls = self.create_top_controls()
        right_layout.addWidget(top_controls)

        send_widget = self.create_send_widget()
        right_layout.addWidget(send_widget)

        bottom_options = self.create_bottom_options()
        right_layout.addWidget(bottom_options)

        return right_group

    def create_top_controls(self):
        """创建顶部控制栏"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.pause_btn = QPushButton("暂停接收")
        self.pause_btn.setMinimumWidth(80)
        self.pause_btn.setMinimumHeight(24)
        left_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("清除显示")
        self.clear_btn.setMinimumWidth(80)
        self.clear_btn.setMinimumHeight(24)
        left_layout.addWidget(self.clear_btn)

        # 搜索区域
        search_label = QLabel("搜索:")
        left_layout.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入搜索关键词...")
        self.search_edit.setMinimumWidth(150)
        self.search_edit.setMinimumHeight(24)
        left_layout.addWidget(self.search_edit)

        self.search_up_btn = QPushButton("previous")
        self.search_up_btn.setToolTip("向上搜索")
        self.search_up_btn.setMinimumHeight(24)
        left_layout.addWidget(self.search_up_btn)

        self.search_down_btn = QPushButton("next")
        self.search_down_btn.setToolTip("向下搜索")
        self.search_down_btn.setMinimumHeight(24)
        left_layout.addWidget(self.search_down_btn)

        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self.timestamp_cb = QCheckBox("时间戳")
        self.timestamp_cb.setChecked(True)
        right_layout.addWidget(self.timestamp_cb)

        self.autoscroll_cb = QCheckBox("自动滚动")
        self.autoscroll_cb.setChecked(True)
        right_layout.addWidget(self.autoscroll_cb)

        self.log_enabled_cb = QCheckBox("启用日志")
        right_layout.addWidget(self.log_enabled_cb)

        self.stay_on_top_cb = QCheckBox("窗口置顶")
        right_layout.addWidget(self.stay_on_top_cb)

        layout.addWidget(left_widget)
        layout.addStretch()
        layout.addWidget(right_widget)
        
        return widget

    def create_bottom_options(self):
        """创建底部选项栏"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.send_hex_cb = QCheckBox("十六进制模式")
        layout.addWidget(self.send_hex_cb)

        self.send_newline_cb = QCheckBox("添加换行符")
        self.send_newline_cb.setChecked(True)
        layout.addWidget(self.send_newline_cb)

        layout.addStretch()
        
        self.data_limit_spin = QComboBox()
        self.data_limit_spin.addItems(
            ["100KB", "500KB", "1MB", "2MB", "5MB", "10MB", "无限制"]
        )
        self.data_limit_spin.setCurrentText("1MB")
        self.data_limit_spin.hide()
        
        return widget

    def create_send_widget(self):
        """创建发送区域"""
        send_widget = QWidget()
        send_layout = QHBoxLayout(send_widget)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.setSpacing(6)
        
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        
        self.send_text_edit = QTextEdit()
        self.send_text_edit.setMinimumHeight(35)
        self.send_text_edit.setMaximumHeight(70)
        self.send_text_edit.setPlaceholderText("输入要发送的数据...")
        self.send_text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 1px;
                background-color: #ffffff;
                margin: 0px;
                line-height: 1.0;
            }
        """)
        text_layout.addWidget(self.send_text_edit)
        text_layout.setAlignment(Qt.AlignTop)
        
        button_layout = QVBoxLayout()
        button_layout.setSpacing(4)
        button_layout.setContentsMargins(0, 1, 0, 0)
        button_layout.setAlignment(Qt.AlignTop)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setMinimumWidth(60)
        self.send_btn.setMinimumHeight(24)
        button_layout.addWidget(self.send_btn)
        
        self.clear_send_btn = QPushButton("清空")
        self.clear_send_btn.setMinimumWidth(60)
        self.clear_send_btn.setMinimumHeight(24)
        button_layout.addWidget(self.clear_send_btn)
        
        send_layout.addWidget(text_container, stretch=1)
        send_layout.addLayout(button_layout)
        
        return send_widget




    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = self.statusBar()
        
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 #f8f9fa, stop:1 #e9ecef);
                border-top: 2px solid #dee2e6;
                color: #495057;
                font-size: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: 500;
                min-height: 20px;
                padding: 1px 4px;
            }
            QStatusBar::item { 
                border: none; 
                background: transparent;
            }
            QLabel {
                color: #495057;
                font-weight: 500;
                padding: 2px 6px;
                background: transparent;
                font-size: 10px;
            }
        """)
        
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.update_status_display()
        
        reset_btn = QPushButton("重置")
        reset_btn.setMaximumWidth(40)
        reset_btn.clicked.connect(self.reset_counters)
        reset_btn.setObjectName("resetButton")
        reset_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 #007bff, stop:1 #0056b3);
                color: white;
                border: 1px solid #0056b3;
                border-radius: 3px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 500;
                min-height: 14px;
                max-height: 14px;
                margin-top: 1px;
                margin-bottom: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 #0056b3, stop:1 #004085);
                border-color: #004085;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 #004085, stop:1 #002752);
                border-color: #002752;
            }
        """)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            background-color: #adb5bd; 
            margin: 2px 6px;
            min-height: 14px;
            max-height: 14px;
        """)
        
        self.status_bar.addPermanentWidget(self.status_label)
        self.status_bar.addPermanentWidget(separator)
        self.status_bar.addPermanentWidget(reset_btn)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件(&F)")
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        view_menu = menubar.addMenu("视图(&V)")
        
        limit_menu = view_menu.addMenu("数据限制(&L)")
        
        limit_actions = []
        limits = ["100KB", "500KB", "1MB", "2MB", "5MB", "10MB", "无限制"]
        for limit in limits:
            action = QAction(limit, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, l=limit: self.set_data_limit(l))
            limit_actions.append(action)
            limit_menu.addAction(action)
        
        current_limit = self.data_limit_spin.currentText()
        for action in limit_actions:
            if action.text() == current_limit:
                action.setChecked(True)
                break
        
        settings_menu = menubar.addMenu("设置(&S)")
        
        font_action = QAction("字体(&F)...", self)
        font_action.triggered.connect(self.open_font_dialog)
        settings_menu.addAction(font_action)
        
        highlight_action = QAction("高亮规则(&H)...", self)
        highlight_action.triggered.connect(self.manage_highlight_rules)
        settings_menu.addAction(highlight_action)
        
        settings_menu.addSeparator()
        
        reset_count_action = QAction("重置计数器(&R)", self)
        reset_count_action.triggered.connect(self.reset_counters)
        settings_menu.addAction(reset_count_action)

    def set_data_limit(self, limit: str):
        """设置数据限制"""
        self.data_limit_spin.setCurrentText(limit)

    def update_status_display(self):
        """更新状态栏显示"""
        self.status_label.setText(f"接收: {self.received_count} 字符  |  发送: {self.sent_count} 字符")

    def reset_counters(self):
        """重置计数器"""
        self.received_count = 0
        self.sent_count = 0
        self.update_status_display()

    def init_connections(self):
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.clear_btn.clicked.connect(self.clear_display)
        self.stay_on_top_cb.toggled.connect(self.toggle_stay_on_top)
        self.log_enabled_cb.toggled.connect(self.toggle_logging)
        self.search_up_btn.clicked.connect(lambda: self.search_data(direction="up"))
        self.search_down_btn.clicked.connect(lambda: self.search_data(direction="down"))
        self.search_edit.returnPressed.connect(
            lambda: self.search_data(direction="down")
        )
        
        self.send_btn.clicked.connect(self.send_data)
        self.clear_send_btn.clicked.connect(self.clear_send_area)
        self.send_text_edit.textChanged.connect(self.update_send_button_state)

        self.port_monitor.ports_changed.connect(self.update_ports)

    
    def update_ports(self, ports_info: List[Dict[str, Any]]):
        current_selection = self.port_combo.currentText()
        self.port_combo.clear()

        for port_info in ports_info:
            display_text = f"{port_info['device']}"
            self.port_combo.addItem(display_text, port_info["device"])

        if current_selection:
            index = self.port_combo.findText(current_selection, Qt.MatchStartsWith)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def toggle_connection(self):
        if not self.is_connected:
            self.connect_serial()
        else:
            self.disconnect_serial()

    def connect_serial(self):
        if self.port_combo.currentData() is None:
            QMessageBox.warning(self, "警告", "请选择一个串口")
            return

        port = self.port_combo.currentData()
        try:
            baudrate = int(self.baudrate_combo.currentText())
        except ValueError:
            QMessageBox.warning(self, "警告", "波特率必须是数字")
            return

        bytesize_map = {"5": 5, "6": 6, "7": 7, "8": 8}
        bytesize = bytesize_map[self.databits_combo.currentText()]

        parity_map = {"None": "N", "Even": "E", "Odd": "O", "Mark": "M", "Space": "S"}
        parity = parity_map[self.parity_combo.currentText()]

        stopbits_map = {"1": 1, "1.5": 1.5, "2": 2}
        stopbits = stopbits_map[self.stopbits_combo.currentText()]

        self.serial_worker = SerialWorker(port, baudrate, bytesize, parity, stopbits)
        self.serial_worker.data_received.connect(self.handle_received_data)
        self.serial_worker.connection_lost.connect(self.handle_connection_lost)

        try:
            self.serial_worker.start()
            self.is_connected = True
            self.connect_btn.setText("断开")
            self.connect_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #008BD3;
                    border: 1px solid #adadad;
                    border-radius: 3px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #0885c4;
                }
                QPushButton:pressed {
                    background-color: #0c7fb9;
                }"""
            )
            self.append_to_display(f"已连接到 {port} (波特率: {baudrate})", "system")
            # 更新发送按钮状态
            self.update_send_button_state()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接失败: {str(e)}")

    def disconnect_serial(self):
        if self.serial_worker:
            self.serial_worker.stop()
            self.serial_worker = None

        self.is_connected = False
        self.connect_btn.setText("连接")
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #eeeeee;
                border: 1px solid #adadad;
                border-radius: 3px;
                color: black;
            }
            QPushButton:hover {
                background-color: #e1e1e1;
            }
            QPushButton:pressed {
                background-color: #cdcdcd;
            }"""
        )
        self.append_to_display("连接已断开", "system")
        # 更新发送按钮状态
        self.update_send_button_state()

    # slot，处理串口数据
    def handle_received_data(self, data: bytes):
        if self.is_paused:
            return
            
        # 更新接收计数器
        self.received_count += len(data)
        self.update_status_display()
        
        try:
            text = data.decode("utf-8", errors="replace")
        except:
            text = data.hex()

        # 限制单次更新文本长度，防止UI卡顿，50KB
        max_chars_per_update = 50000
        if len(text) > max_chars_per_update:
            for i in range(0, len(text), max_chars_per_update):
                chunk = text[i : i + max_chars_per_update]
                self.append_to_display(chunk, "received")
                if self.log_enabled_cb.isChecked() and self.log_file:
                    self.write_to_log(chunk)
        else:
            self.append_to_display(text, "received")
            if self.log_enabled_cb.isChecked() and self.log_file:
                self.write_to_log(text)

    def handle_connection_lost(self):
        self.disconnect_serial()
        QMessageBox.warning(self, "警告", "串口连接丢失")

    # √，TODO:日志的时间戳与TextBrower此时间戳不一致
    def append_to_display(self, text: str, msg_type: str = "normal"):
        cursor = self.data_display.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 开关串口日志直接添加时间戳
        if msg_type == "system":
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            # 使用HTML格式设置时间戳为灰色
            cursor.insertHtml(
                f'<span style="color: #888888;">[{timestamp}]</span> {text}<br>'
            )
        
        # 发送的数据显示为绿色
        elif msg_type == "sent":
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            cursor.insertHtml(
                f'<span style="color: #888888;">[{timestamp}]</span> <span style="color: #008000;">{text}</span><br>'
            )

        # 接收的数据在勾选时间戳后才添加时间戳
        elif msg_type == "received":
            if self.timestamp_cb.isChecked():
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                lines = text.splitlines(True)
                for i, line in enumerate(lines):
                    if i == 0:
                        # 第一行添加时间戳
                        line_text = line.rstrip("\r\n")
                        cursor.insertHtml(
                            f'<span style="color: #bbbbbb;">[{timestamp}]</span> {line_text}<br>'
                        )
                    else:
                        # 后续行缩进对齐
                        line_text = line.rstrip("\r\n")
                        if line_text.strip():  # 非空行
                            cursor.insertHtml(f"{line_text}<br>")
                        else:
                            # 空行直接换行
                            cursor.insertHtml("<br>")
            else:
                # 不显示时间戳时，使用纯文本保持原始格式
                cursor.insertText(text)

        else:
            cursor.insertText(text)

        # 检查数据限制并清理旧数据
        self.check_data_limit()

        # 自动滚动到最新数据
        if self.autoscroll_cb.isChecked():
            scrollbar = self.data_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("恢复接收")
            self.pause_btn.setStyleSheet("QPushButton { background-color: #ff9800; }")
        else:
            self.pause_btn.setText("暂停接收")
            self.pause_btn.setStyleSheet("")

    def toggle_stay_on_top(self):
        """切换窗口置顶状态"""
        if self.stay_on_top_cb.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)

        self.show()

    def clear_display(self):
        self.data_display.clear()

    def toggle_logging(self, enabled):
        """切换日志功能"""
        if enabled:
            log_dir = os.path.join(os.getcwd(), "log")
            os.makedirs(log_dir, exist_ok=True)
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"log_{timestamp}.log"
            self.log_file = os.path.join(log_dir, filename)
        else:
            self.log_file = None

    def write_to_log(self, text: str):
        if not self.log_file:
            return

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                if self.timestamp_cb.isChecked():
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    f.write(f"[{timestamp}] {text}")
                else:
                    f.write(text)
        except Exception as e:
            print(f"写入日志失败: {e}")

    def check_data_limit(self):
        """检查数据限制并清理旧数据"""
        limit_text = self.data_limit_spin.currentText()
        if limit_text == "无限制":
            return

        limit_kb = int(
            limit_text.replace("KB", "").replace("MB", "000").replace("无限制", "0")
        )
        if limit_kb == 0:
            return

        document = self.data_display.document()
        current_text = document.toPlainText()
        current_length = len(current_text.encode("utf-8"))

        # 如果超出限制，删除前面的数据
        if current_length > limit_kb * 1024:
            # 计算需要删除的字符数（保留最后70%的数据，减少清理频率）
            chars_to_keep = int(len(current_text) * 0.7)
            new_text = current_text[-chars_to_keep:] if chars_to_keep > 0 else ""

            # 使用信号阻塞来优化性能
            old_state = self.data_display.blockSignals(True)
            scrollbar = self.data_display.verticalScrollBar()
            current_scroll = scrollbar.value()

            self.data_display.clear()
            self.data_display.setPlainText(new_text)

            # 恢复信号和滚动位置
            self.data_display.blockSignals(old_state)
            max_scroll = scrollbar.maximum()
            new_scroll = max(0, current_scroll - (len(current_text) - chars_to_keep))
            scrollbar.setValue(min(new_scroll, max_scroll))

    def open_font_dialog(self):
        """打开字体选择对话框"""
        current_font = self.data_display.font()
        result = QFontDialog.getFont(current_font, self, "选择字体")
        
        if result[0]:
            self.apply_font(result[1])

    def apply_font(self, font):
        """应用字体设置"""
        self.data_display.setFont(font)
        self.send_text_edit.setFont(font)

        # 保存设置
        self.settings.setValue("font_family", font.family())
        self.settings.setValue("font_size", font.pointSize())

    def search_data(self, direction="down"):
        """搜索功能"""
        search_text = self.search_edit.text()
        if not search_text:
            return

        document = self.data_display.document()
        current_cursor = self.data_display.textCursor()

        # 确保光标有效
        if current_cursor.isNull():
            if direction == "down":
                current_cursor = QTextCursor(document)
                current_cursor.movePosition(QTextCursor.Start)
            else:
                current_cursor = QTextCursor(document)
                current_cursor.movePosition(QTextCursor.End)

        if direction == "down":
            cursor = document.find(search_text, current_cursor)

            if cursor.isNull():
                cursor = document.find(search_text, QTextCursor(document))
                if not cursor.isNull():
                    QMessageBox.information(self, "搜索", "已到达末尾，从头开始搜索")
                else:
                    QMessageBox.information(self, "搜索", "未找到匹配的文本")
        else:
            cursor = document.find(
                search_text, current_cursor, QTextDocument.FindBackward
            )

            if cursor.isNull():
                end_cursor = QTextCursor(document)
                end_cursor.movePosition(QTextCursor.End)
                cursor = document.find(
                    search_text, end_cursor, QTextDocument.FindBackward
                )
                if not cursor.isNull():
                    QMessageBox.information(self, "搜索", "已到达开头，从末尾开始搜索")
                else:
                    QMessageBox.information(self, "搜索", "未找到匹配的文本")

        if not cursor.isNull():
            self.data_display.setTextCursor(cursor)
            self.data_display.ensureCursorVisible()
    
    def send_data(self):
        """发送数据到串口"""
        if not self.is_connected or not self.serial_worker:
            QMessageBox.warning(self, "警告", "请先连接串口")
            return
            
        text = self.send_text_edit.toPlainText()
        if not text:
            return
            
        try:
            if self.send_hex_cb.isChecked():
                # 十六进制模式
                hex_text = text.replace(' ', '').replace('\n', '').replace('\r', '')
                if len(hex_text) % 2 != 0:
                    QMessageBox.warning(self, "错误", "十六进制数据长度必须为偶数")
                    return
                data = bytes.fromhex(hex_text)
            else:
                if self.send_newline_cb.isChecked():
                    text += '\r\n'
                data = text.encode('utf-8')
                
            if self.serial_worker.send_data(data):
                self.sent_count += len(data)
                self.update_status_display()
                
                if self.send_hex_cb.isChecked():
                    display_text = f"发送(HEX): {data.hex(' ').upper()}"
                else:
                    display_text = f"发送: {text.rstrip()}"
                self.append_to_display(display_text, "sent")
            else:
                QMessageBox.warning(self, "错误", "发送数据失败")
                
        except ValueError as e:
            QMessageBox.warning(self, "错误", f"十六进制格式错误: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"发送失败: {str(e)}")
    
    def clear_send_area(self):
        """清空发送区域"""
        self.send_text_edit.clear()
    
    def update_send_button_state(self):
        """更新发送按钮状态"""
        has_text = bool(self.send_text_edit.toPlainText().strip())
        self.send_btn.setEnabled(has_text and self.is_connected)

    def manage_highlight_rules(self):
        """管理高亮规则"""
        dialog = HighlightRulesDialog(self, self.highlight_rules.copy())
        if dialog.exec() == QDialog.Accepted:
            self.highlight_rules = dialog.get_rules()
            if self.highlighter:
                self.highlighter.update_rules(self.highlight_rules)
            self.save_highlight_rules()

    # 从注册表加载设置
    def load_settings(self):
        """加载设置"""
        self.baudrate_combo.setCurrentText(self.settings.value("baudrate", "115200"))
        self.databits_combo.setCurrentText(self.settings.value("databits", "8"))
        self.parity_combo.setCurrentText(self.settings.value("parity", "None"))
        self.stopbits_combo.setCurrentText(self.settings.value("stopbits", "1"))
        self.timestamp_cb.setChecked(self.settings.value("timestamp", True, type=bool))
        self.autoscroll_cb.setChecked(
            self.settings.value("autoscroll", True, type=bool)
        )
        self.stay_on_top_cb.setChecked(
            self.settings.value("stay_on_top", False, type=bool)
        )
        self.data_limit_spin.setCurrentText(self.settings.value("data_limit", "1MB"))

        font_family = self.settings.value("font_family", "Consolas")
        font_size = int(self.settings.value("font_size", 10))

        font = QFont(font_family, font_size)
        self.apply_font(font)

        self.load_highlight_rules()

    def load_highlight_rules(self):
        """加载高亮规则"""
        self.highlight_rules.clear()
        settings = QSettings("SerialPortTool", "HighlightRules")
        size = settings.beginReadArray("rules")
        for i in range(size):
            settings.setArrayIndex(i)
            pattern = settings.value("pattern", "")
            color_name = settings.value("color", "#ff0000")
            is_regex = settings.value("is_regex", False, type=bool)
            # 向后兼容：如果enabled属性不存在，默认启用
            enabled = settings.value("enabled", True, type=bool)
            if pattern:
                color = QColor(color_name)
                rule = HighlightRule(pattern, color, is_regex, enabled)
                self.highlight_rules.append(rule)
        settings.endArray()

    def save_highlight_rules(self):
        """保存高亮规则"""
        settings = QSettings("SerialPortTool", "HighlightRules")
        settings.beginWriteArray("rules")
        for i, rule in enumerate(self.highlight_rules):
            settings.setArrayIndex(i)
            settings.setValue("pattern", rule.pattern)
            settings.setValue("color", rule.color.name())
            settings.setValue("is_regex", rule.is_regex)
            settings.setValue("enabled", rule.enabled)
        settings.endArray()

    def save_settings(self):
        """保存设置"""
        self.settings.setValue("baudrate", self.baudrate_combo.currentText())
        self.settings.setValue("databits", self.databits_combo.currentText())
        self.settings.setValue("parity", self.parity_combo.currentText())
        self.settings.setValue("stopbits", self.stopbits_combo.currentText())
        self.settings.setValue("timestamp", self.timestamp_cb.isChecked())
        self.settings.setValue("autoscroll", self.autoscroll_cb.isChecked())
        self.settings.setValue("stay_on_top", self.stay_on_top_cb.isChecked())
        self.settings.setValue("data_limit", self.data_limit_spin.currentText())

    def closeEvent(self, event):
        """关闭事件"""
        self.save_settings()
        if self.serial_worker:
            self.serial_worker.stop()
        self.port_monitor.stop()
        event.accept()
