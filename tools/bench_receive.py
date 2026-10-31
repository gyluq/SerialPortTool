#!/usr/bin/env python
"""Receive-path benchmark for SerialPortTool.

Every scenario drives the real widget through ``handle_received_bytes``, the
same entry point the reader thread uses, so the numbers include HTML escaping,
insertion, trimming and (optionally) painting.

Scenarios
    single   largest single payload accepted, and how long it takes
    stream   sustained throughput in MB/s
    loss     sequence-number audit: does any byte vanish inside the limit?
    pause    what the paused buffer does under overload
    memory   process RSS growth per capacity setting
    send     cost of pasting and queueing a very large outbound payload
    loop     end-to-end through pyserial's loop:// and the real reader thread

Usage
    python tools/bench_receive.py                 # all in-process scenarios
    python tools/bench_receive.py --only stream
    python tools/bench_receive.py --only loss --total-mb 4 --limit 1MB
    python tools/bench_receive.py --only loop --total-mb 2
    python tools/bench_receive.py --native        # paint with the real platform

The offscreen platform is used by default: text layout cost is the same, but
no window is shown. Pass --native to measure real painting as well.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LINE_BYTES = 64
CHUNK_BYTES = 4096
SEQ_RE = re.compile(r"#(\d{6}) ")


def build_payload(lines: int, start: int = 1) -> bytes:
    """Fixed-width lines so a 4 KiB chunk always ends on a line boundary."""
    out = []
    for index in range(start, start + lines):
        head = f"#{index:06d} "
        body = "TEMP=26.5C HUM=48% RAW="
        filler = "x" * (LINE_BYTES - 1 - len(head) - len(body))
        out.append(head + body + filler + "\n")
    return "".join(out).encode("ascii")


def bytes_to_lines(size: int) -> int:
    return max(1, size // LINE_BYTES)


def mbps(byte_count: int, seconds: float) -> float:
    return byte_count / (1024 * 1024) / seconds if seconds > 0 else float("inf")


def human_bytes(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def rss_mb() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


def make_window(limit_label: str = "无限制", autoscroll: bool = True, timestamps: bool = True):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from serial_tool.ui.main_window import SerialPortTool, apply_stylesheet
    from serial_tool.ui.settings_store import SettingsStore

    app = QApplication.instance() or QApplication([])
    apply_stylesheet(app)

    tmp = tempfile.NamedTemporaryFile(suffix=".ini", delete=False)
    tmp.close()
    store = SettingsStore(QSettings(tmp.name, QSettings.IniFormat))
    window = SerialPortTool(store=store)
    window.config.limit_label = limit_label
    window.autoscroll_check.setChecked(autoscroll)
    window.timestamp_check.setChecked(timestamps)
    window.resize(1200, 800)
    window.show()
    return app, window


def feed(window, payload: bytes, chunk: int = CHUNK_BYTES) -> float:
    """Push payload in chunks, return the seconds spent inside the slot."""
    start = time.perf_counter()
    for offset in range(0, len(payload), chunk):
        window.handle_received_bytes(payload[offset : offset + chunk])
    return time.perf_counter() - start


def safe_ratio(done: int, total: int) -> str:
    return f"{done / total * 100:.2f}%"


# --------------------------------------------------------------------- single
def scenario_single(sizes: list[int], multi_sizes: list[int]) -> None:
    print("\n[单次输入] 一次 handle_received_bytes 能吞多少")
    print(f"{'形态':<10}{'大小':>10}{'耗时':>12}{'吞吐':>14}{'文档字符':>12}")
    print("-" * 60)

    for shape, shape_sizes in (("单行单次", sizes), ("多行分片", multi_sizes)):
        for size in shape_sizes:
            _, window = make_window()
            try:
                if shape == "单行单次":
                    # One call carrying one huge unbroken line: no newline, so
                    # it becomes a single paragraph. Not reachable from a real
                    # port (read() returns at most 4096 bytes) but it is the
                    # worst case a paste or a test harness can trigger.
                    payload = (b"A" * (size - 1)) + b"\n"
                    start = time.perf_counter()
                    window.handle_received_bytes(payload)
                    elapsed = time.perf_counter() - start
                else:
                    payload = build_payload(bytes_to_lines(size))
                    payload = payload[:size]
                    elapsed = feed(window, payload)
                chars = window.display.document().characterCount()
                print(
                    f"{shape:<10}{human_bytes(size):>10}{elapsed * 1000:>10.1f}ms"
                    f"{mbps(size, elapsed):>11.2f}MB/s{chars:>12,}"
                )
            finally:
                window.close()


# --------------------------------------------------------------------- stream
def scenario_stream(total_mb: float, limits: list[str]) -> None:
    total = int(total_mb * 1024 * 1024)
    print(f"\n[持续吞吐] 连续灌入 {total_mb:g} MB，4 KiB 一块")
    print(f"{'容量上限':<10}{'总耗时':>11}{'吞吐':>13}{'块均':>11}{'行数':>10}{'RSS增量':>11}")
    print("-" * 68)

    for limit in limits:
        _, window = make_window(limit_label=limit)
        try:
            payload = build_payload(bytes_to_lines(total))
            payload = payload[:total]
            before_rss = rss_mb()
            chunks = 0

            start = time.perf_counter()
            for offset in range(0, len(payload), CHUNK_BYTES):
                window.handle_received_bytes(payload[offset : offset + CHUNK_BYTES])
                chunks += 1
            elapsed = time.perf_counter() - start

            print(
                f"{limit:<10}{elapsed:>9.2f}s{mbps(total, elapsed):>10.2f}MB/s"
                f"{elapsed / chunks * 1000:>9.2f}ms{len(window._block_chars):>10,}"
                f"{rss_mb() - before_rss:>9.0f}MB"
            )
        finally:
            window.close()


# ----------------------------------------------------------------------- loss
def audit(window) -> tuple[int, int, int]:
    """Return (found, lowest, highest) sequence numbers in the document."""
    text = window.display.toPlainText()
    seqs = [int(m) for m in SEQ_RE.findall(text)]
    if not seqs:
        return 0, 0, 0
    return len(seqs), min(seqs), max(seqs)


def scenario_loss(total_mb: float, limit: str) -> None:
    total = int(total_mb * 1024 * 1024)
    expected = bytes_to_lines(total)
    print(f"\n[丢包审计] 灌入 {expected:,} 行，每行带序号，容量上限 = {limit}")

    _, window = make_window(limit_label=limit)
    try:
        payload = build_payload(expected)
        start = time.perf_counter()
        for offset in range(0, len(payload), CHUNK_BYTES):
            window.handle_received_bytes(payload[offset : offset + CHUNK_BYTES])
        elapsed = time.perf_counter() - start

        found, low, high = audit(window)
        chars = len(window.display.toPlainText())
        span = high - low + 1 if found else 0
        holes = span - found
        contiguous = holes == 0

        print(f"  耗时        : {elapsed:.2f}s ({mbps(total, elapsed):.2f} MB/s)")
        print(f"  注入行数    : {expected:,}")
        print(f"  文档保留    : {found:,} 行，字符 {chars:,}")
        print(f"  序号区间    : {low:,} .. {high:,}（跨度 {span:,}）")
        print(f"  区间内空洞  : {holes:,} 行 -> {'连续，无中间丢失' if contiguous else '存在空洞'}")
        print(f"  头部被回收  : {low - 1:,} 行（容量策略，预期行为）")
        if limit == "无限制":
            ok = found == expected and contiguous
            print(f"  结论        : {'全部到达' if ok else '有数据未显示'}")
        else:
            limit_chars = limit_to_chars(limit)
            print(f"  文档字符是否 <= 上限: {chars <= limit_chars} ({chars:,} / {limit_chars:,})")
        window._pause_buffer.clear()
    finally:
        window.close()


def limit_to_chars(label: str) -> int:
    from serial_tool.ui.main_window import limit_to_chars as convert

    return convert(label)


# ---------------------------------------------------------------------- pause
def scenario_pause(total_mb: float, limit: str) -> None:
    total = int(total_mb * 1024 * 1024)
    expected = bytes_to_lines(total)
    print(f"\n[暂停缓冲] 暂停后灌入 {total_mb:g} MB，上限 {limit}，恢复后看保留情况")

    _, window = make_window(limit_label=limit)
    try:
        window._toggle_pause()
        payload = build_payload(expected)
        start = time.perf_counter()
        for offset in range(0, len(payload), CHUNK_BYTES):
            window.handle_received_bytes(payload[offset : offset + CHUNK_BYTES])
        elapsed = time.perf_counter() - start
        buffered_chars = window._pause_chars
        buffered_entries = len(window._pause_buffer)

        resume_start = time.perf_counter()
        window._toggle_pause()
        resume_elapsed = time.perf_counter() - resume_start

        found, low, high = audit(window)
        span = high - low + 1 if found else 0
        holes = span - found
        print(f"  暂停写入耗时: {elapsed:.2f}s ({mbps(total, elapsed):.2f} MB/s)")
        print(f"  缓冲区        : {buffered_entries:,} 块 / {buffered_chars:,} 字符")
        print(f"  恢复渲染耗时  : {resume_elapsed:.2f}s")
        print(f"  恢复后保留    : {found:,} 行（序号 {low:,}..{high:,}，空洞 {holes:,}）")
        print(f"  暂停期间丢弃  : {expected - found:,} 行（超出缓冲上限，设计如此）")
    finally:
        window.close()


# --------------------------------------------------------------------- memory
def scenario_memory(sizes_mb: list[float], limit: str) -> None:
    print(f"\n[内存占用] 容量上限 {limit}")
    print(f"{'累计灌入':>10}{'RSS':>12}{'增量':>10}{'文档字符':>14}{'块数':>10}")
    print("-" * 58)

    _, window = make_window(limit_label=limit)
    base = rss_mb()
    try:
        print(f"{'基线':>10}{base:>10.0f}MB{0:>8.0f}MB"
              f"{window.display.document().characterCount():>14,}{0:>10,}")
        fed = 0
        for size_mb in sizes_mb:
            size = int(size_mb * 1024 * 1024)
            payload = build_payload(bytes_to_lines(size), start=fed // LINE_BYTES + 1)
            for offset in range(0, len(payload), CHUNK_BYTES):
                window.handle_received_bytes(payload[offset : offset + CHUNK_BYTES])
            fed += len(payload)
            current = rss_mb()
            print(
                f"{fed / 1024 / 1024:>8.0f}MB{current:>10.0f}MB{current - base:>8.0f}MB"
                f"{window.display.document().characterCount():>14,}"
                f"{len(window._block_chars):>10,}"
            )
    finally:
        window.close()


# ----------------------------------------------------------------------- send
def scenario_send(sizes: list[int]) -> None:
    print("\n[发送侧] 大块粘贴与入队")
    print(f"{'大小':>10}{'setPlainText':>16}{'toPlainText':>15}{'编码+入队':>14}{'校验':>8}")
    print("-" * 66)

    from serial_tool import core

    _, window = make_window()
    try:
        for size in sizes:
            text = ("AT+RESET\n" * (size // 9 + 1))[:size]
            start = time.perf_counter()
            window.send_edit.setPlainText(text)
            set_elapsed = time.perf_counter() - start

            start = time.perf_counter()
            read_back = window.send_edit.toPlainText()
            get_elapsed = time.perf_counter() - start

            start = time.perf_counter()
            core.codec.encode_text(read_back, False)
            queue_elapsed = time.perf_counter() - start

            ok = "一致" if read_back == text else "不一致"
            print(
                f"{human_bytes(size):>10}{set_elapsed * 1000:>14.1f}ms"
                f"{get_elapsed * 1000:>13.1f}ms{queue_elapsed * 1000:>12.1f}ms{ok:>8}"
            )
            window.send_edit.clear()
    finally:
        window.close()


# ----------------------------------------------------------------------- loop
class BufferedPipeTransport:
    """In-memory stand-in for a serial driver buffer.

    pyserial's loop:// holds only 4 KiB and blocks inside write() when full,
    which caps a benchmark at that buffer size instead of at the code under
    test. A real driver buffer is larger and absorbs bursts, so this transport
    does the same: writes never block, reads return what is available or wait
    for the same 10 ms timeout the real transport uses.
    """

    TIMEOUT = 0.01

    def __init__(self, capacity: int = 256 * 1024) -> None:
        import threading

        self._buffer = bytearray()
        self._capacity = capacity
        self._lock = threading.Lock()
        self._open = True

    @property
    def is_open(self) -> bool:
        return self._open

    def read(self, size: int) -> bytes:
        deadline = time.perf_counter() + self.TIMEOUT
        while True:
            with self._lock:
                if self._buffer:
                    chunk = bytes(self._buffer[:size])
                    del self._buffer[:size]
                    return chunk
            if time.perf_counter() >= deadline:
                return b""
            time.sleep(0.0005)

    def write(self, data: bytes) -> None:
        with self._lock:
            # Never block: an overflowing buffer would deadlock the reader
            # thread, which is also the thread that drains writes.
            if len(self._buffer) < self._capacity:
                self._buffer.extend(data)

    def close(self) -> None:
        self._open = False


def scenario_loop(total_mb: float, limit: str) -> None:
    total = int(total_mb * 1024 * 1024)
    expected = bytes_to_lines(total)
    print(f"\n[端到端] 真实读取线程 + 驱动缓冲模拟，灌入 {total_mb:g} MB，上限 {limit}")

    from PySide6.QtWidgets import QApplication

    app, window = make_window(limit_label=limit)
    try:
        window._transport_factory = lambda _params: BufferedPipeTransport()
        window.port_combo.addItem("LOOP", "LOOP")
        window.port_combo.setCurrentIndex(window.port_combo.count() - 1)
        window._connect()
        if window._session is None or not window._session.is_open:
            print("  无法建立 loop 连接，跳过")
            return

        payload = build_payload(expected)
        session = window._session

        def writer() -> None:
            # Stay ~64 KiB ahead of what the UI has acknowledged, so the
            # reader thread always has data waiting and never pays the 10 ms
            # idle timeout.
            offset = 0
            chunk_size = 8192
            while offset < len(payload):
                chunk = payload[offset : offset + chunk_size]
                session.submit_write(chunk)
                offset += len(chunk)
                deadline = time.time() + 10
                while (
                    window.counters.received < offset - 64 * 1024
                    and time.time() < deadline
                ):
                    time.sleep(0.0002)

        start = time.perf_counter()
        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        while window.counters.received < len(payload):
            QApplication.processEvents()
            if time.perf_counter() - start > 120:
                break
            time.sleep(0.0005)
        elapsed = time.perf_counter() - start
        thread.join(timeout=1)

        received = window.counters.received
        found, low, high = audit(window)
        print(f"  串口收到      : {received:,} / {len(payload):,} 字节 ({safe_ratio(received, len(payload))})")
        print(f"  耗时          : {elapsed:.2f}s ({mbps(received, elapsed):.2f} MB/s)")
        print(f"  显示行数      : {found:,} / {expected:,}")
        print(f"  序号区间      : {low:,}..{high:,}")
        window._disconnect()
    finally:
        window.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="SerialPortTool receive benchmark")
    parser.add_argument(
        "--only",
        choices=["single", "stream", "loss", "pause", "memory", "send", "loop"],
        action="append",
        help="run only the listed scenarios (repeatable)",
    )
    parser.add_argument("--total-mb", type=float, default=2.0)
    parser.add_argument("--limit", default="1MB")
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()

    if not args.native:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    selected = args.only or ["single", "stream", "loss", "pause", "memory", "send"]

    if "single" in selected:
        scenario_single([4 * 1024, 64 * 1024, 256 * 1024], [64 * 1024, 1024 * 1024, 4 * 1024 * 1024])
    if "stream" in selected:
        scenario_stream(args.total_mb, ["100KB", "1MB", "无限制"])
    if "loss" in selected:
        scenario_loss(args.total_mb, "无限制")
        scenario_loss(args.total_mb, args.limit)
    if "pause" in selected:
        scenario_pause(args.total_mb, args.limit)
    if "memory" in selected:
        scenario_memory([1, 1, 2, 4], "无限制")
        scenario_memory([1, 1, 2, 4], args.limit)
    if "send" in selected:
        scenario_send([64 * 1024, 1024 * 1024])
    if "loop" in selected:
        scenario_loop(min(args.total_mb, 4.0), args.limit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
