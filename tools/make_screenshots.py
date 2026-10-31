"""Regenerate the screenshots embedded in README.md / README.zh-CN.md.

Runs the real window on the native platform (not offscreen) because Qt's
offscreen backend renders CJK glyphs as boxes. Traffic is injected through the
same entry point the serial thread uses, so nothing here depends on hardware.

Usage:
    python tools/make_screenshots.py            # writes docs/images/*.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from serial_tool.core.highlight import Rule, compile_rules  # noqa: E402
from serial_tool.core.render import Line, Style  # noqa: E402
from serial_tool.ui.main_window import SerialPortTool, apply_stylesheet  # noqa: E402
from serial_tool.ui.rules_dialog import RulesDialog  # noqa: E402

OUT = ROOT / "docs" / "images"

RULES = [
    Rule("ERROR", "#ff6b6b"),
    Rule(r"OK|PASS", "#4ade80", is_regex=True),
    Rule(r"TEMP=\d+\.\d", "#60a5fa", is_regex=True),
]

TRANSCRIPT_HEAD = [
    Line("已连接 COM3 · 115200 8N1 · 串口已打开", Style.SYSTEM, "16:04:11.902"),
    Line("AT+VER?", Style.SENT),
    Line("AT+VER?", Style.SENT),
    Line("FW 1.4.2  build 2026-08-11", Style.RECEIVED, "16:04:12.118"),
    Line("boot: self-test OK", Style.RECEIVED),
]


def _transcript() -> list[Line]:
    """A plausible device session: readings, frames, an error, a recovery."""
    lines = list(TRANSCRIPT_HEAD)
    seconds = 12.4
    for index in range(14):
        seconds += 0.35
        stamp = f"16:04:{int(seconds):02d}.{int((seconds % 1) * 1000):03d}"
        temp = 23.4 + (index % 5) * 0.1
        rssi = -67 - (index % 3)
        lines.append(Line(f"TEMP={temp:.1f}C  HUM={40 + index % 3}%  RSSI={rssi}dBm", Style.RECEIVED, stamp))
        lines.append(Line(f"frame 0x1A{0x2B + index:02X} len=32 crc=0x{0x9F31 + index * 7:04X}", Style.RECEIVED))
        if index == 3:
            lines.append(Line("ERROR: CRC mismatch, frame dropped", Style.RECEIVED))
        if index == 6:
            lines.append(Line("AT+READ?", Style.SENT))
        if index == 8:
            lines.append(Line("frame 0x1A34 len=32 crc=0x4C08  OK", Style.RECEIVED))
    lines.append(Line("heartbeat", Style.RECEIVED))
    return lines


def _pump(app: QApplication, rounds: int = 12) -> None:
    for _ in range(rounds):
        app.processEvents()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    apply_stylesheet(app)

    window = SerialPortTool()
    window.timestamp_check.setChecked(True)
    window.send_edit.setPlainText("AT+READ?")

    window._rules = compile_rules(list(RULES))  # noqa: SLF001
    window.highlighter.set_rules(window._rules)

    transcript = _transcript()
    for line in transcript:
        window._append_line(line)  # noqa: SLF001
    received = sum(len(x.text) + 1 for x in transcript if x.style is Style.RECEIVED)
    sent = sum(len(x.text) + 1 for x in transcript if x.style is Style.SENT)
    window.counters.add_received(received)
    window.counters.add_sent(sent)
    window._update_status()  # noqa: SLF001

    # A port name in the picker: the shot is a demo, and an empty combo reads
    # like the app failed to enumerate anything.
    if window.port_combo.count() == 0:
        window.port_combo.addItem("COM3")
    window.port_combo.setCurrentIndex(0)

    # Force the console state for each shot instead of relying on the window
    # width, so a scaled display cannot flip the breakpoint mid-capture.
    window._manual_console = True  # noqa: SLF001
    window.resize(1400, 880)
    window.show()
    _pump(app)
    window._apply_console_state()  # noqa: SLF001
    _pump(app)
    window.grab().save(str(OUT / "main-window.png"))

    # Narrow: console folds away, the one-line bar takes over.
    window._manual_console = None  # noqa: SLF001
    window.resize(760, 660)
    _pump(app)
    window._apply_console_state()  # noqa: SLF001
    _pump(app)
    window.grab().save(str(OUT / "console-collapsed.png"))

    dialog = RulesDialog(None, list(window._rules))  # noqa: SLF001
    dialog.resize(620, 400)
    dialog.show()
    _pump(app)
    dialog.grab().save(str(OUT / "rules-dialog.png"))
    dialog.close()

    window.close()
    print(f"screenshots -> {OUT}")
    for path in sorted(OUT.glob("*.png")):
        print(" ", path.name, path.stat().st_size // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
