"""Main window: layout, event wiring and rendering only; all decisions are
delegated to serial_tool.core."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable, Deque

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QFont, QTextCursor
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFontDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from serial_tool.core import codec, render
from serial_tool.core.config import AppConfig
from serial_tool.core.counters import Counter
from serial_tool.core.highlight import Rule
from serial_tool.core.logfile import LogWriter, build_log_path
from serial_tool.core.params import (
    BAUD_CHOICES,
    DATABITS_CHOICES,
    PARITY_LABELS,
    STOPBITS_LABELS,
    Parity,
    SerialParams,
    validate,
)
from serial_tool.core.retention import trim_plan
from serial_tool.core.session import PortInfo, SerialSession, Transport, list_ports
from serial_tool.ui.highlighter import RuleHighlighter
from serial_tool.ui.rules_dialog import RulesDialog
from serial_tool.ui.settings_store import SettingsStore
from serial_tool.ui.styles import (
    APP_STYLESHEET,
    CONNECT_BUTTON_CONNECTED,
    CONNECT_BUTTON_IDLE,
    DISPLAY_STYLE,
    PAUSE_BUTTON_ACTIVE,
)

LIMIT_LABELS: tuple[str, ...] = ("100KB", "500KB", "1MB", "2MB", "5MB", "10MB", "无限制")
PORT_REFRESH_MS = 1000
READ_IDLE_SLEEP_MS = 10
APP_DIR = Path(__file__).resolve().parents[2]


def limit_to_chars(label: str) -> int:
    """Convert a capacity label into a character count; 0 means unlimited."""
    if label == "无限制":
        return 0
    if label.endswith("MB"):
        return int(float(label[:-2]) * 1024 * 1024)
    if label.endswith("KB"):
        return int(float(label[:-2]) * 1024)
    return 0


def now_stamp() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


class ReaderThread(QThread):
    """Serial worker thread: read data and drain the write queue."""

    data_received = Signal(bytes)
    connection_lost = Signal(str)

    def __init__(self, session: SerialSession) -> None:
        super().__init__()
        self._session = session
        self._running = True

    def run(self) -> None:  # noqa: D102
        while self._running:
            try:
                self._session.drain_writes()
                data = self._session.read_once()
            except Exception as exc:  # e.g. the port was unplugged
                self.connection_lost.emit(str(exc))
                return
            if data:
                self.data_received.emit(data)
            else:
                self.msleep(READ_IDLE_SLEEP_MS)

    def stop(self) -> None:
        self._running = False
        self.wait(1500)


class SerialPortTool(QMainWindow):
    def __init__(
        self,
        store: SettingsStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("串口工具")

        self._store = store or SettingsStore()
        self.config: AppConfig = self._store.load_config()
        self._rules: list[Rule] = self._store.load_rules()

        self._session: SerialSession | None = None
        self._reader: ReaderThread | None = None
        self._transport_factory: Callable[[SerialParams], Transport] | None = None
        self._log_writer: LogWriter | None = None

        self._paused = False
        self._pause_buffer: Deque[tuple[str, str | None]] = deque()
        self._pause_chars = 0
        self._block_chars: list[int] = []
        self._block_total = 0

        self.counters = Counter()
        self._ports: list[PortInfo] = []

        self._build_ui()
        self._build_menu()
        self._build_status_bar()
        self._wire()
        self._restore_config()

        self._port_timer = QTimer(self)
        self._port_timer.setInterval(PORT_REFRESH_MS)
        self._port_timer.timeout.connect(self._refresh_ports)
        self._port_timer.start()
        self._refresh_ports()

    # ---------------------------------------------------------------- layout

    def _build_ui(self) -> None:
        self.setGeometry(100, 100, 1200, 800)
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(2)
        splitter.setChildrenCollapsible(False)

        self.display = QTextBrowser()
        self.display.setStyleSheet(DISPLAY_STYLE)
        self.display.setFont(QFont(self.config.font_family, self.config.font_size))
        self.highlighter = RuleHighlighter(self.display.document(), self._rules)

        control = QWidget()
        control.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        control_layout = QHBoxLayout(control)
        control_layout.setContentsMargins(6, 6, 6, 6)
        control_layout.setSpacing(8)
        control_layout.addWidget(self._build_connection_panel())
        control_layout.addWidget(self._build_control_panel())

        splitter.addWidget(self.display)
        splitter.addWidget(control)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        outer.addWidget(splitter, stretch=1)

    def _build_connection_panel(self) -> QGroupBox:
        group = QGroupBox("串口连接")
        grid = QGridLayout(group)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(6)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self.baud_combo = QComboBox()
        self.baud_combo.setMinimumWidth(80)
        self.baud_combo.addItems([str(b) for b in BAUD_CHOICES])
        self.baud_combo.setCurrentText("115200")

        self.databits_combo = QComboBox()
        self.databits_combo.addItems([str(b) for b in DATABITS_CHOICES])
        self.databits_combo.setCurrentText("8")

        self.parity_combo = QComboBox()
        self.parity_combo.addItems(list(PARITY_LABELS))

        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems([STOPBITS_LABELS[s] for s in sorted(STOPBITS_LABELS)])

        self.connect_button = QPushButton("连接")
        self.connect_button.setMinimumWidth(80)

        grid.addWidget(QLabel("端口:"), 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(QLabel("波特率:"), 0, 2)
        grid.addWidget(self.baud_combo, 0, 3)
        grid.addWidget(QLabel("数据位:"), 1, 0)
        grid.addWidget(self.databits_combo, 1, 1)
        grid.addWidget(QLabel("校验位:"), 1, 2)
        grid.addWidget(self.parity_combo, 1, 3)
        grid.addWidget(QLabel("停止位:"), 2, 0)
        grid.addWidget(self.stopbits_combo, 2, 1)
        grid.addWidget(self.connect_button, 2, 2, 1, 2)
        return group

    def _build_control_panel(self) -> QGroupBox:
        group = QGroupBox("功能控制")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Top row: pause / clear / search / toggles
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        self.pause_button = QPushButton("暂停接收")
        self.clear_button = QPushButton("清除显示")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入搜索关键词...")
        self.search_edit.setMinimumWidth(150)
        self.search_prev_button = QPushButton("previous")
        self.search_prev_button.setToolTip("向上搜索")
        self.search_next_button = QPushButton("next")
        self.search_next_button.setToolTip("向下搜索")

        for widget in (
            self.pause_button,
            self.clear_button,
            QLabel("搜索:"),
            self.search_edit,
            self.search_prev_button,
            self.search_next_button,
        ):
            top_layout.addWidget(widget)

        top_layout.addStretch()

        self.timestamp_check = QCheckBox("时间戳")
        self.autoscroll_check = QCheckBox("自动滚动")
        self.log_check = QCheckBox("启用日志")
        self.ontop_check = QCheckBox("窗口置顶")
        for widget in (
            self.timestamp_check,
            self.autoscroll_check,
            self.log_check,
            self.ontop_check,
        ):
            top_layout.addWidget(widget)

        # Send area
        send_row = QWidget()
        send_layout = QHBoxLayout(send_row)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.setSpacing(6)

        self.send_edit = QTextEdit()
        self.send_edit.setObjectName("sendEdit")
        self.send_edit.setPlaceholderText("输入要发送的数据...")
        self.send_edit.setMinimumHeight(35)
        self.send_edit.setMaximumHeight(70)

        self.send_button = QPushButton("发送")
        self.send_clear_button = QPushButton("清空")
        self.send_button.setMinimumWidth(60)
        self.send_clear_button.setMinimumWidth(60)

        button_column = QVBoxLayout()
        button_column.setSpacing(4)
        button_column.addWidget(self.send_button)
        button_column.addWidget(self.send_clear_button)

        send_layout.addWidget(self.send_edit, stretch=1)
        send_layout.addLayout(button_column)

        # Bottom row: send mode
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)
        self.hex_check = QCheckBox("十六进制模式")
        self.newline_check = QCheckBox("添加换行符")
        bottom_layout.addWidget(self.hex_check)
        bottom_layout.addWidget(self.newline_check)
        bottom_layout.addStretch()

        layout.addWidget(top)
        layout.addWidget(send_row)
        layout.addWidget(bottom)
        return group

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)

        self.status_label = QLabel()
        self.reset_button = QPushButton("重置")
        self.reset_button.setMaximumWidth(48)
        self.reset_button.clicked.connect(self._reset_counters)

        status.addPermanentWidget(self.status_label)
        status.addPermanentWidget(self.reset_button)
        self._update_status()

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        quit_action = QAction("退出(&X)", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("视图(&V)")
        limit_menu = view_menu.addMenu("数据限制(&L)")
        self._limit_actions: dict[str, QAction] = {}
        self._limit_group = QActionGroup(self)
        self._limit_group.setExclusive(True)
        for label in LIMIT_LABELS:
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, l=label: self._set_limit(l))
            self._limit_group.addAction(action)
            limit_menu.addAction(action)
            self._limit_actions[label] = action

        settings_menu = menubar.addMenu("设置(&S)")
        font_action = QAction("字体(&F)...", self)
        font_action.triggered.connect(self._choose_font)
        settings_menu.addAction(font_action)

        rules_action = QAction("高亮规则(&H)...", self)
        rules_action.triggered.connect(self._manage_rules)
        settings_menu.addAction(rules_action)

        settings_menu.addSeparator()
        reset_action = QAction("重置计数器(&R)", self)
        reset_action.triggered.connect(self._reset_counters)
        settings_menu.addAction(reset_action)

    def _wire(self) -> None:
        self.connect_button.clicked.connect(self._toggle_connection)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.clear_button.clicked.connect(self._clear_display)
        self.send_button.clicked.connect(self._send)
        self.send_clear_button.clicked.connect(self.send_edit.clear)
        self.send_edit.textChanged.connect(self._update_send_state)
        self.search_edit.returnPressed.connect(lambda: self._search("down"))
        self.search_next_button.clicked.connect(lambda: self._search("down"))
        self.search_prev_button.clicked.connect(lambda: self._search("up"))
        self.log_check.toggled.connect(self._toggle_log)
        self.ontop_check.toggled.connect(self._toggle_on_top)
        self.hex_check.toggled.connect(self._on_send_mode_changed)
        self.autoscroll_check.toggled.connect(lambda _: self._save_config())

    def _restore_config(self) -> None:
        cfg = self.config
        self._restoring = True
        try:
            self.baud_combo.setCurrentText(str(cfg.baudrate))
            self.databits_combo.setCurrentText(str(cfg.databits))
            for label, parity in PARITY_LABELS.items():
                if parity.value == cfg.parity:
                    self.parity_combo.setCurrentText(label)
                    break
            for stopbits, label in STOPBITS_LABELS.items():
                if abs(stopbits - cfg.stopbits) < 1e-9:
                    self.stopbits_combo.setCurrentText(label)
                    break

            self.timestamp_check.setChecked(cfg.show_timestamp)
            self.autoscroll_check.setChecked(cfg.autoscroll)
            self.ontop_check.setChecked(cfg.always_on_top)
            self.hex_check.setChecked(cfg.hex_mode)
            self.newline_check.setChecked(cfg.append_newline)
            self.log_check.setChecked(cfg.log_enabled)
            font = QFont(cfg.font_family, cfg.font_size)
            self.display.setFont(font)
            self.send_edit.setFont(font)

            if cfg.limit_label in self._limit_actions:
                self._limit_actions[cfg.limit_label].setChecked(True)
        finally:
            self._restoring = False
        self._update_send_state()

    # ------------------------------------------------------------ config saving

    def _save_config(self) -> None:
        if getattr(self, "_restoring", False):
            return
        cfg = self.config
        cfg.baudrate = int(self.baud_combo.currentText())
        cfg.databits = int(self.databits_combo.currentText())
        cfg.parity = PARITY_LABELS[self.parity_combo.currentText()].value
        cfg.stopbits = {v: k for k, v in STOPBITS_LABELS.items()}[
            self.stopbits_combo.currentText()
        ]
        cfg.show_timestamp = self.timestamp_check.isChecked()
        cfg.autoscroll = self.autoscroll_check.isChecked()
        cfg.always_on_top = self.ontop_check.isChecked()
        cfg.hex_mode = self.hex_check.isChecked()
        cfg.append_newline = self.newline_check.isChecked()
        cfg.log_enabled = self.log_check.isChecked()
        font = self.display.font()
        cfg.font_family = font.family()
        cfg.font_size = font.pointSize()
        self._store.save_config(cfg)

    # ------------------------------------------------------------ ports and connection

    def _refresh_ports(self) -> None:
        ports = list_ports()
        if [p.device for p in ports] == [p.device for p in self._ports]:
            return

        current = self.port_combo.currentData()
        self._ports = ports
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(port.device, port.device)
            index = self.port_combo.count() - 1
            self.port_combo.setItemData(index, f"{port.device} - {port.description}", Qt.ToolTipRole)
        self.port_combo.blockSignals(False)

        if current:
            index = self.port_combo.findData(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def _current_params(self) -> SerialParams:
        return SerialParams(
            port=self.port_combo.currentData() or "",
            baudrate=int(self.baud_combo.currentText()),
            databits=int(self.databits_combo.currentText()),
            parity=PARITY_LABELS[self.parity_combo.currentText()],
            stopbits={v: k for k, v in STOPBITS_LABELS.items()}[
                self.stopbits_combo.currentText()
            ],
        )

    def _toggle_connection(self) -> None:
        if self._session is None:
            self._connect()
        else:
            self._disconnect()

    def _connect(self) -> None:
        params = self._current_params()
        errors = validate(params)
        if errors:
            QMessageBox.warning(self, "警告", errors[0])
            return

        transport = self._transport_factory(params) if self._transport_factory else None
        session = SerialSession(params, transport=transport)
        try:
            session.open()
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"连接失败: {exc}")
            return

        self._session = session
        self._reader = ReaderThread(session)
        self._reader.data_received.connect(self.handle_received_bytes)
        self._reader.connection_lost.connect(self._handle_connection_lost)
        self._reader.start()

        self.connect_button.setText("断开")
        self.connect_button.setStyleSheet(CONNECT_BUTTON_CONNECTED)
        self._append_line(
            render.Line(f"已连接到 {params.port} (波特率: {params.baudrate})", render.Style.SYSTEM, now_stamp())
        )
        self._update_send_state()

    def _disconnect(self) -> None:
        if self._reader is not None:
            self._reader.stop()
            self._reader = None
        if self._session is not None:
            self._session.close()
            self._session = None

        self.connect_button.setText("连接")
        self.connect_button.setStyleSheet(CONNECT_BUTTON_IDLE)
        self._append_line(render.Line("连接已断开", render.Style.SYSTEM, now_stamp()))
        self._update_send_state()

    def _handle_connection_lost(self, reason: str) -> None:
        self._disconnect()
        QMessageBox.warning(self, "警告", f"串口连接丢失\n{reason}")

    # ---------------------------------------------------------------- receiving

    def handle_received_bytes(self, data: bytes) -> None:
        """Receive entry point. Tests come through here too, as if the device sent bytes."""
        self.counters.add_received(len(data))
        self._update_status()

        text = codec.decode_text(data)
        stamp = now_stamp()
        # The checkbox governs both the display and the log, so resolve it once.
        show_stamp = stamp if self.timestamp_check.isChecked() else None

        if self._log_writer is not None:
            self._log_writer.write(text, show_stamp)

        if self._paused:
            self._buffer_while_paused(text, show_stamp)
            return

        self._append_received(text, show_stamp)

    def _buffer_while_paused(self, text: str, stamp: str | None) -> None:
        self._pause_buffer.append((text, stamp))
        self._pause_chars += len(text)
        limit = limit_to_chars(self.config.limit_label)
        while limit > 0 and self._pause_chars > limit and len(self._pause_buffer) > 1:
            old_text, _ = self._pause_buffer.popleft()
            self._pause_chars -= len(old_text)

    def _append_received(self, text: str, stamp: str | None) -> None:
        lines = text.splitlines() or [""]
        for index, line_text in enumerate(lines):
            self._append_line(
                render.Line(line_text, render.Style.RECEIVED, stamp if index == 0 else None)
            )

    def _append_line(self, line: render.Line) -> None:
        # append() appends a block in O(1); inserting into a cursor at the end
        # re-lays out the document on every call and slows down linearly with
        # the number of lines already shown. append() also keeps the user's
        # selection, because it does not move the visible cursor.
        self.display.append(render.render_paragraph_html(line))

        size = len(line.text) + 1
        self._block_chars.append(size)
        self._block_total += size
        self._trim_display()

        if self.autoscroll_check.isChecked():
            bar = self.display.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _clear_display(self) -> None:
        """Clear the view and the reclamation bookkeeping together."""
        self.display.clear()
        self._block_chars.clear()
        self._block_total = 0

    def _trim_display(self) -> None:
        limit = limit_to_chars(self.config.limit_label)
        # The running total keeps this check O(1); recomputing it from the
        # block list on every single line would dominate the receive path.
        if limit <= 0 or self._block_total <= limit:
            return

        plan = trim_plan(self._block_chars, limit)
        if plan.delete_blocks <= 0:
            return

        document = self.display.document()
        start = QTextCursor(document)
        start.movePosition(QTextCursor.Start)
        end = QTextCursor(document)
        end.movePosition(QTextCursor.Start)
        deleted = 0
        for _ in range(plan.delete_blocks):
            if not end.movePosition(QTextCursor.NextBlock):
                break
            deleted += 1
        if deleted <= 0:
            return
        start.setPosition(end.position(), QTextCursor.KeepAnchor)
        start.removeSelectedText()
        self._block_total -= sum(self._block_chars[:deleted])
        del self._block_chars[:deleted]

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self.pause_button.setText("恢复接收")
            self.pause_button.setStyleSheet(PAUSE_BUTTON_ACTIVE)
            return

        self.pause_button.setText("暂停接收")
        self.pause_button.setStyleSheet("")
        buffered = list(self._pause_buffer)
        self._pause_buffer.clear()
        self._pause_chars = 0
        for text, stamp in buffered:
            self._append_received(text, stamp)

    # ---------------------------------------------------------------- sending

    def _send(self) -> None:
        if self._session is None or not self._session.is_open:
            QMessageBox.warning(self, "警告", "请先连接串口")
            return

        text = self.send_edit.toPlainText()
        if not text:
            return

        if self.hex_check.isChecked():
            try:
                data = codec.parse_hex(text)
            except codec.HexFormatError as exc:
                QMessageBox.warning(self, "错误", str(exc))
                return
            display_text = f"发送(HEX): {codec.format_hex(data)}"
        else:
            data = codec.encode_text(text, self.newline_check.isChecked())
            display_text = f"发送: {text.rstrip()}"

        self._session.submit_write(data)
        self.counters.add_sent(len(data))
        self._update_status()
        self._append_line(render.Line(display_text, render.Style.SENT, now_stamp()))

    def _on_send_mode_changed(self, hex_mode: bool) -> None:
        self.newline_check.setEnabled(not hex_mode)
        self._save_config()

    def _update_send_state(self) -> None:
        connected = self._session is not None and self._session.is_open
        has_text = bool(self.send_edit.toPlainText().strip())
        self.send_button.setEnabled(connected and has_text)

    # ---------------------------------------------------------------- misc

    def _search(self, direction: str) -> None:
        keyword = self.search_edit.text()
        if not keyword:
            return

        document = self.display.document()
        cursor = self.display.textCursor()
        flags = (
            QTextDocument.FindBackward
            if direction == "up"
            else QTextDocument.FindFlags()
        )

        found = document.find(keyword, cursor, flags)
        if found.isNull():
            fallback = QTextCursor(document)
            fallback.movePosition(
                QTextCursor.Start if direction == "down" else QTextCursor.End
            )
            found = document.find(keyword, fallback, flags)
            if found.isNull():
                QMessageBox.information(self, "搜索", "未找到匹配的文本")
                return
            QMessageBox.information(self, "搜索", "已环绕搜索")

        self.display.setTextCursor(found)
        self.display.ensureCursorVisible()

    def _set_limit(self, label: str) -> None:
        self.config.limit_label = label
        action = self._limit_actions.get(label)
        if action is not None:
            action.setChecked(True)
        self._store.save_config(self.config)
        self._trim_display()

    def _choose_font(self) -> None:
        # Use the instance API: the static QFontDialog.getFont() returns
        # (ok, font) in PySide6 6.x, which is easy to unpack the wrong way.
        dialog = QFontDialog(self.display.font(), self)
        dialog.setWindowTitle("选择字体")
        if dialog.exec() != QDialog.Accepted:
            return
        font = dialog.currentFont()
        self.display.setFont(font)
        self.send_edit.setFont(font)
        self._save_config()

    def _manage_rules(self) -> None:
        dialog = RulesDialog(self, self._rules)
        if dialog.exec() != QDialog.Accepted:
            return
        self._rules = dialog.rules()
        self.highlighter.set_rules(self._rules)
        self._store.save_rules(self._rules)

    def _toggle_on_top(self, enabled: bool) -> None:
        flags = self.windowFlags()
        if enabled:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()
        self._save_config()

    def _toggle_log(self, enabled: bool) -> None:
        if enabled:
            path = build_log_path(APP_DIR, datetime.now())
            try:
                self._log_writer = LogWriter(path)
            except OSError as exc:
                QMessageBox.warning(self, "警告", f"无法创建日志文件: {exc}")
                self.log_check.setChecked(False)
                return
        else:
            if self._log_writer is not None:
                self._log_writer.close()
                self._log_writer = None
        self._save_config()

    def _update_status(self) -> None:
        self.status_label.setText(self.counters.text())

    def _reset_counters(self) -> None:
        self.counters.reset()
        self._update_status()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._port_timer.stop()
        if self._reader is not None:
            self._reader.stop()
            self._reader = None
        if self._session is not None:
            self._session.close()
            self._session = None
        if self._log_writer is not None:
            self._log_writer.close()
            self._log_writer = None
        self._save_config()
        self._store.save_rules(self._rules)
        event.accept()


def apply_stylesheet(app) -> None:
    app.setStyleSheet(APP_STYLESHEET)
