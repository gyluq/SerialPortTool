"""The launcher must hand Qt a multi-resolution icon.

A single large PNG is resampled by Qt for the 16 px title bar, which blurs, so
the shipped .ico has to carry frames drawn for each size. These tests lock that
down without needing a display: QIcon parses the container on its own.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QIcon

import main

ROOT = Path(__file__).resolve().parents[2]


def _sizes(icon: QIcon) -> set[tuple[int, int]]:
    return {(s.width(), s.height()) for s in icon.availableSizes()}


def test_ico_carries_every_taskbar_size(qapp):
    sizes = _sizes(QIcon(str(ROOT / "icon.ico")))

    assert (16, 16) in sizes, "title bar frame missing"
    assert (256, 256) in sizes, "large frame missing"
    assert len(sizes) >= 7, f"expected a full ladder of frames, got {sorted(sizes)}"


def test_png_is_big_enough_to_downscale(qapp):
    sizes = _sizes(QIcon(str(ROOT / "icon.png")))

    assert sizes, "icon.png did not load"
    assert max(width for width, _ in sizes) >= 256


def test_load_icon_prefers_the_ico(qapp, tmp_path):
    for name in ("icon.png", "icon.ico"):
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())

    icon = main.load_icon(tmp_path)

    assert icon is not None
    # Only the .ico can report a 16x16 frame; a PNG would expose just its own size.
    assert (16, 16) in _sizes(icon)


def test_load_icon_falls_back_to_the_png(qapp, tmp_path):
    (tmp_path / "icon.png").write_bytes((ROOT / "icon.png").read_bytes())

    icon = main.load_icon(tmp_path)

    assert icon is not None and not icon.isNull()


def test_load_icon_returns_none_when_nothing_is_usable(qapp, tmp_path):
    (tmp_path / "icon.png").write_bytes(b"not an image")

    assert main.load_icon(tmp_path) is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
