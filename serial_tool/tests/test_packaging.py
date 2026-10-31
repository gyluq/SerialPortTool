"""Where the packaged app keeps files it expects to survive a restart.

A onefile PyInstaller build unpacks the package into a temporary directory
(_MEIxxxx) that is deleted when the process exits, so anything derived from
__file__ is lost. Logs must not be derived from __file__.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from serial_tool.core.config import app_base_dir, resource_dir
from serial_tool.core.logfile import build_log_path


class TestAppBaseDir:
    def test_source_run_uses_the_project_root(self, tmp_path):
        """Running from the checkout: serial_tool/ui/main_window.py -> repo root."""
        package_file = tmp_path / "repo" / "serial_tool" / "ui" / "main_window.py"
        package_file.parent.mkdir(parents=True)

        base = app_base_dir(
            is_frozen=False,
            executable=tmp_path / "python.exe",
            package_file=package_file,
        )

        assert base == (tmp_path / "repo").resolve()

    def test_frozen_run_uses_the_executable_directory(self, tmp_path):
        """A onefile build must not resolve paths inside the temp unpack dir."""
        exe = tmp_path / "apps" / "SerialPortTool" / "SerialPortTool.exe"
        exe.parent.mkdir(parents=True)
        unpacked = tmp_path / "_MEI123" / "serial_tool" / "ui" / "main_window.py"

        base = app_base_dir(is_frozen=True, executable=exe, package_file=unpacked)

        assert base == exe.parent.resolve()

    def test_frozen_ignores_the_package_location(self, tmp_path):
        """Two different temp dirs must give the same answer, since the exe is the anchor."""
        exe = tmp_path / "apps" / "SerialPortTool.exe"
        exe.parent.mkdir(parents=True)

        first = app_base_dir(True, exe, tmp_path / "_MEI111" / "a.py")
        second = app_base_dir(True, exe, tmp_path / "_MEI222" / "b.py")

        assert first == second == exe.parent.resolve()

    def test_paths_are_absolute(self, tmp_path, monkeypatch):
        """A relative anchor would make the log directory depend on the working dir."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "serial_tool" / "ui").mkdir(parents=True)

        base = app_base_dir(
            is_frozen=False,
            executable=Path("python.exe"),
            package_file=Path("serial_tool/ui/main_window.py"),
        )

        assert base.is_absolute()


class TestResourceDir:
    def test_frozen_uses_the_unpack_directory(self, tmp_path):
        """Bundled assets really are unpacked next to the entry script."""
        base = resource_dir(
            is_frozen=True,
            bundle_dir=str(tmp_path / "_MEI123"),
            package_file=tmp_path / "_MEI123" / "main.py",
        )

        assert base == tmp_path / "_MEI123"

    def test_source_run_uses_the_script_directory(self, tmp_path):
        script = tmp_path / "repo" / "main.py"

        base = resource_dir(is_frozen=False, bundle_dir=None, package_file=script)

        assert base == (tmp_path / "repo").resolve()

    def test_frozen_without_bundle_dir_falls_back(self, tmp_path):
        base = resource_dir(is_frozen=True, bundle_dir=None, package_file=tmp_path / "main.py")

        assert base == tmp_path.resolve()


class TestLogPathUnderBase:
    def test_log_expands_to_the_executable_directory_when_frozen(self, tmp_path):
        exe = tmp_path / "apps" / "SerialPortTool" / "SerialPortTool.exe"
        exe.parent.mkdir(parents=True)
        base = app_base_dir(True, exe, tmp_path / "_MEI123" / "serial_tool" / "ui" / "main_window.py")

        path = build_log_path(base, datetime(2026, 10, 31, 15, 4, 5))

        assert path.parent.parent == exe.parent.resolve()
        assert path.name == "log_20261031_150405.log"
