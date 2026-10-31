"""Critical UI paths: the behaviours most likely to regress."""

from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6")

from serial_tool.core.render import Line, Style


class TestConnection:
    def test_connect_switches_button(self, connected):
        window, _ = connected
        assert window._session.is_open
        assert window.connect_button.text() == "断开"

    def test_disconnect_switches_back(self, connected):
        window, _ = connected
        window._disconnect()
        assert window._session is None
        assert window.connect_button.text() == "连接"


class TestReceive:
    def test_plain_text_shown(self, connected):
        window, _ = connected
        window.handle_received_bytes(b"hello world")
        assert "hello world" in window.display.toPlainText()

    def test_html_special_chars_are_escaped(self, connected):
        """<, & and > sent by the device must be shown verbatim, not parsed as HTML."""
        window, _ = connected
        window.handle_received_bytes(b"a < b & c > d")
        assert "a < b & c > d" in window.display.toPlainText()

    def test_multiline_kept_as_separate_lines(self, connected):
        window, _ = connected
        window.handle_received_bytes(b"line1\nline2\nline3")
        text = window.display.toPlainText()
        assert "line1" in text and "line2" in text and "line3" in text

    def test_counters_grow(self, connected):
        window, _ = connected
        before = window.counters.received
        window.handle_received_bytes(b"12345")
        assert window.counters.received == before + 5


class TestPause:
    def test_paused_data_hidden_then_flushed(self, connected):
        """Data must not be lost while paused; it is flushed on resume."""
        window, _ = connected
        window._toggle_pause()
        window.handle_received_bytes(b"during-pause")
        assert "during-pause" not in window.display.toPlainText()

        window._toggle_pause()
        assert "during-pause" in window.display.toPlainText()

    def test_pause_keeps_counting(self, connected):
        window, _ = connected
        window._toggle_pause()
        before = window.counters.received
        window.handle_received_bytes(b"abcdef")
        assert window.counters.received == before + 6


class TestSend:
    def test_text_send_goes_to_queue(self, connected):
        window, fake = connected
        window.send_edit.setPlainText("hi")
        window._send()
        window._session.drain_writes()
        assert fake.written == [b"hi"]

    def test_append_newline(self, connected):
        window, fake = connected
        window.newline_check.setChecked(True)
        window.send_edit.setPlainText("hi")
        window._send()
        window._session.drain_writes()
        assert fake.written == [b"hi\r\n"]

    def test_hex_send(self, connected):
        window, fake = connected
        window.hex_check.setChecked(True)
        window.send_edit.setPlainText("01 0A FF")
        window._send()
        window._session.drain_writes()
        assert fake.written == [b"\x01\x0a\xff"]

    def test_send_counts_bytes(self, connected):
        window, _ = connected
        window.send_edit.setPlainText("abc")
        window._send()
        assert window.counters.sent == 3

    def test_send_button_disabled_when_empty(self, connected):
        window, _ = connected
        window.send_edit.setPlainText("")
        window._update_send_state()
        assert not window.send_button.isEnabled()

    def test_send_button_enabled_with_text(self, connected):
        window, _ = connected
        window.send_edit.setPlainText("x")
        assert window.send_button.isEnabled()


class TestHighlight:
    def test_rule_marks_matching_text(self, window):
        """A plain-string rule must be painted onto the block."""
        from serial_tool.core.highlight import Rule, compile_rule

        window.highlighter.set_rules(
            [compile_rule(Rule(pattern="ERROR", color="#ff0000"))]
        )
        window.display.setPlainText("ERROR here")
        window.highlighter.rehighlight()

        block = window.display.document().firstBlock()
        assert block.layout().formats(), "rule should produce a char format"

    def test_disabled_rule_does_not_paint(self, window):
        from serial_tool.core.highlight import Rule, compile_rule

        window.highlighter.set_rules(
            [compile_rule(Rule(pattern="ERROR", color="#ff0000", enabled=False))]
        )
        window.display.setPlainText("ERROR here")
        window.highlighter.rehighlight()

        assert not window.display.document().firstBlock().layout().formats()

    def test_rules_round_trip_through_store(self, store):
        """Rules must survive a save/load cycle, otherwise they vanish on restart."""
        from serial_tool.core.highlight import Rule, compile_rule

        rules = [
            compile_rule(Rule(pattern="TEMP", color="#00ff00")),
            compile_rule(Rule(pattern=r"\d+ms", color="#ffaa00", is_regex=True)),
        ]
        store.save_rules(rules)
        loaded = store.load_rules()

        assert [r.pattern for r in loaded] == ["TEMP", r"\d+ms"]
        assert loaded[1].is_regex is True
        assert loaded[1].color == "#ffaa00"


class TestTimestamp:
    def test_only_first_line_of_chunk_gets_stamp(self, connected):
        """A multi-line chunk carries one timestamp, on its first line only."""
        window, _ = connected
        window.timestamp_check.setChecked(True)
        window.display.clear()
        window.handle_received_bytes(b"aaa\nbbb\nccc")

        text = window.display.toPlainText()
        lines = [ln for ln in text.splitlines() if ln.strip()]
        stamped = [ln for ln in lines if ln.lstrip().startswith("[")]
        assert len(stamped) == 1
        assert "aaa" in stamped[0]
        assert "bbb" in lines[1]

    def test_stamp_suppressed_when_checkbox_off(self, connected):
        window, _ = connected
        window.timestamp_check.setChecked(False)
        window.display.clear()
        window.handle_received_bytes(b"no-stamp")

        text = window.display.toPlainText()
        assert "[" not in text


class TestPersistence:
    def test_settings_survive_reopen(self, qapp, store):
        """Baud rate and toggles must come back on the next start."""
        from serial_tool.ui.main_window import SerialPortTool

        first = SerialPortTool(store=store)
        first.baud_combo.setCurrentText("921600")
        first.autoscroll_check.setChecked(False)
        first.hex_check.setChecked(True)
        first._save_config()
        first.close()

        second = SerialPortTool(store=store)
        try:
            assert second.baud_combo.currentText() == "921600"
            assert second.autoscroll_check.isChecked() is False
            assert second.hex_check.isChecked() is True
        finally:
            second.close()

    def test_font_survives_reopen(self, qapp, store):
        """A chosen font must be restored, otherwise it silently resets each start."""
        from PySide6.QtGui import QFont

        from serial_tool.ui.main_window import SerialPortTool

        first = SerialPortTool(store=store)
        first.display.setFont(QFont("Courier New", 18))
        first.send_edit.setFont(QFont("Courier New", 18))
        first._save_config()
        first.close()

        second = SerialPortTool(store=store)
        try:
            assert second.display.font().family() == "Courier New"
            assert second.display.font().pointSize() == 18
            assert second.send_edit.font().pointSize() == 18
        finally:
            second.close()


class TestFontChoice:
    """Regression: the static QFontDialog.getFont() returns (ok, font) in PySide6 6.x,
    so unpacking it as (font, ok) fed a bool into setFont and left the window stuck."""

    def test_accepted_applies_font_to_both_editors(self, window, monkeypatch):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QDialog

        import serial_tool.ui.main_window as mw

        class FakeDialog:
            def __init__(self, initial, parent=None):
                self._font = QFont("Courier New", 17)

            def setWindowTitle(self, title):
                self.title = title

            def exec(self):
                return QDialog.Accepted

            def currentFont(self):
                return self._font

        monkeypatch.setattr(mw, "QFontDialog", FakeDialog)
        window._choose_font()

        assert window.display.font().family() == "Courier New"
        assert window.send_edit.font().family() == "Courier New"

    def test_chosen_size_survives_the_stylesheet(self, window, monkeypatch):
        """A font-size in the global stylesheet used to pin QTextEdit and turn the
        font picker into a no-op: pointSize() came back as -1 and nothing redrew."""
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QDialog

        import serial_tool.ui.main_window as mw

        class FakeDialog:
            def __init__(self, initial, parent=None):
                pass

            def setWindowTitle(self, title):
                pass

            def exec(self):
                return QDialog.Accepted

            def currentFont(self):
                return QFont("Courier New", 17)

        monkeypatch.setattr(mw, "QFontDialog", FakeDialog)
        window._choose_font()

        assert window.display.font().pointSize() == 17
        assert window.send_edit.font().pointSize() == 17

    def test_render_changes_after_font_change(self, window, monkeypatch):
        """The visible proof: the same text must not paint identically at two sizes."""
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QApplication, QDialog

        import serial_tool.ui.main_window as mw

        window.resize(600, 300)
        window.show()
        window._append_line(Line("HELLO 12345", Style.RECEIVED, "00:00:00.000"))
        QApplication.processEvents()
        before = window.display.grab().toImage()

        class BigDialog:
            def __init__(self, initial, parent=None):
                pass

            def setWindowTitle(self, title):
                pass

            def exec(self):
                return QDialog.Accepted

            def currentFont(self):
                return QFont("Courier New", 26)

        monkeypatch.setattr(mw, "QFontDialog", BigDialog)
        window._choose_font()
        QApplication.processEvents()
        after = window.display.grab().toImage()

        assert before != after

    def test_rejected_leaves_font_untouched(self, window, monkeypatch):
        from PySide6.QtWidgets import QDialog

        import serial_tool.ui.main_window as mw

        before = window.display.font().family()

        class FakeDialog:
            def __init__(self, initial, parent=None):
                pass

            def setWindowTitle(self, title):
                pass

            def exec(self):
                return QDialog.Rejected

            def currentFont(self):
                raise AssertionError("must not be read when the dialog is rejected")

        monkeypatch.setattr(mw, "QFontDialog", FakeDialog)
        window._choose_font()

        assert window.display.font().family() == before

    def test_window_still_closable_after_choosing_font(self, window, monkeypatch):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QDialog

        import serial_tool.ui.main_window as mw

        class FakeDialog:
            def __init__(self, initial, parent=None):
                pass

            def setWindowTitle(self, title):
                pass

            def exec(self):
                return QDialog.Accepted

            def currentFont(self):
                return QFont("Consolas", 13)

        monkeypatch.setattr(mw, "QFontDialog", FakeDialog)
        window.show()
        window._choose_font()
        window.close()
        assert not window.isVisible()


class TestRetention:
    def test_trim_removes_old_lines_keeps_recent(self, window):
        """Recent content must still be there after old data is reclaimed."""
        window._clear_display()
        for i in range(300):
            window._append_line(Line(f"line-{i}", Style.RECEIVED, None))

        # 300 lines are well past 1 KiB, so the next append triggers reclamation
        window.config.limit_label = "1KB"
        window._trim_display()

        text = window.display.toPlainText()
        assert "line-299" in text
        assert "line-0\n" not in text

    def test_trim_preserves_html_formatting(self, connected):
        """Reclamation deletes whole blocks, so surviving lines keep their color markup
        and the document has no broken tags."""
        window, _ = connected
        window._clear_display()
        for i in range(200):
            window._append_line(Line(f"row-{i} 数据", Style.RECEIVED, "12:00:00.000"))

        window.config.limit_label = "1KB"
        window._trim_display()

        html = window.display.toHtml()
        assert "row-199" in window.display.toPlainText()
        assert html.count("<p") == window.display.document().blockCount()


class TestStreaming:
    """Guards for the append-based receive path.

    Inserting each line with QTextCursor.insertHtml() at the end of the
    document costs time proportional to the document size, which made a 64 KB
    burst take seconds. append() is constant time, so these tests pin both the
    speed and the layout it produces.
    """

    def test_one_block_per_line(self, window):
        window._clear_display()
        for i in range(5):
            window._append_line(Line(f"row-{i}", Style.RECEIVED, None))

        assert window.display.document().blockCount() == 5
        assert window.display.toPlainText() == "row-0\nrow-1\nrow-2\nrow-3\nrow-4"

    def test_received_multi_line_has_no_blank_rows(self, window):
        window._clear_display()
        window.timestamp_check.setChecked(False)
        window.handle_received_bytes(b"a\nb\nc\n")

        assert window.display.toPlainText() == "a\nb\nc"
        assert window.display.document().blockCount() == 3

    def test_thousands_of_lines_stay_fast(self, window):
        window._clear_display()
        start = time.perf_counter()
        for _ in range(4000):
            window._append_line(Line("x" * 60, Style.RECEIVED, None))
        elapsed = time.perf_counter() - start

        # 4000 lines take well under a second now; the old cursor insertion
        # needed over a minute for this, so 5 s only catches a real regression.
        assert elapsed < 5.0, f"4000 lines took {elapsed:.1f}s"
