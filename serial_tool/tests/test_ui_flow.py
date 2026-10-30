"""Critical UI paths: the behaviours most likely to regress."""

from __future__ import annotations

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


class TestRetention:
    def test_trim_removes_old_lines_keeps_recent(self, window):
        """Recent content must still be there after old data is reclaimed."""
        window.display.clear()
        window._block_chars.clear()
        for i in range(300):
            window._append_line(Line(f"line-{i}", Style.RECEIVED, None))

        # Drop the limit to 200 characters to force reclamation
        window.config.limit_label = "100KB"
        window._block_chars = [9] * 300
        window._trim_display()

        text = window.display.toPlainText()
        assert "line-299" in text

    def test_trim_preserves_html_formatting(self, connected):
        """Reclamation deletes whole blocks, so surviving lines keep their color markup
        and the document has no broken tags."""
        window, _ = connected
        window.display.clear()
        window._block_chars.clear()
        for i in range(200):
            window._append_line(Line(f"row-{i} 数据", Style.RECEIVED, "12:00:00.000"))

        window._block_chars = [12] * 200
        window.config.limit_label = "100KB"
        window._trim_display()

        html = window.display.toHtml()
        assert "row-199" in window.display.toPlainText()
        assert html.count("<p") == window.display.document().blockCount()
