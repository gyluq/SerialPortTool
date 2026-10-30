from datetime import datetime
from pathlib import Path

from serial_tool.core.logfile import LogWriter, build_log_path


class TestBuildLogPath:
    def test_name_and_folder(self):
        path = build_log_path(Path("/app"), datetime(2026, 10, 30, 22, 5, 9))
        assert path == Path("/app/log/log_20261030_220509.log")

    def test_depends_on_base_dir_only(self):
        a = build_log_path(Path("/a"), datetime(2026, 1, 2, 3, 4, 5))
        b = build_log_path(Path("/b"), datetime(2026, 1, 2, 3, 4, 5))
        assert a.parent.parent == Path("/a")
        assert b.parent.parent == Path("/b")


class TestLogWriter:
    def test_creates_file_and_dir(self, tmp_path):
        target = tmp_path / "log" / "log_x.log"
        with LogWriter(target) as writer:
            writer.write("hello", "12:00:00.000")
        assert target.exists()

    def test_timestamp_prefix(self, tmp_path):
        target = tmp_path / "a.log"
        with LogWriter(target) as writer:
            writer.write("hello", "12:00:00.000")
        assert "[12:00:00.000] hello" in target.read_text(encoding="utf-8")

    def test_without_timestamp(self, tmp_path):
        target = tmp_path / "b.log"
        with LogWriter(target) as writer:
            writer.write("hello", None)
        assert target.read_text(encoding="utf-8") == "hello"

    def test_appends_sequentially(self, tmp_path):
        target = tmp_path / "c.log"
        with LogWriter(target) as writer:
            writer.write("one", None)
            writer.write("two", None)
        assert target.read_text(encoding="utf-8") == "onetwo"

    def test_write_after_close_is_ignored(self, tmp_path):
        target = tmp_path / "d.log"
        writer = LogWriter(target)
        writer.write("one", None)
        writer.close()
        writer.write("two", None)
        assert "two" not in target.read_text(encoding="utf-8")

    def test_close_is_idempotent(self, tmp_path):
        writer = LogWriter(tmp_path / "e.log")
        writer.close()
        writer.close()
