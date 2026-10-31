"""Generate the application icon (icon.png + multi-size icon.ico).

Pure Pillow, no external assets: every shape is drawn at 4x and downsampled,
so the result is crisp at 16 px and at 256 px alike.

Usage:
    python tools/make_icon.py                 # write icon.png + icon.ico
    python tools/make_icon.py --preview       # candidate sheet -> .user/icon-candidates.png
    python tools/make_icon.py --variant c     # pick a variant (a|c)
"""

from __future__ import annotations

import argparse
import io
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SS = 4  # supersampling factor
MASTER = 1024  # master square in final pixels

# Palette follows the app accent (#007bff) and its dark receive panel (#1e1e1e).
TOP = (62, 158, 255)
BOTTOM = (0, 84, 208)
FACE = (15, 32, 60)
WHITE = (255, 255, 255)


def _scaled(pts, s):
    return [(x * s, y * s) for x, y in pts]


def _unit(ax, ay):
    length = math.hypot(ax, ay) or 1.0
    return ax / length, ay / length


def rounded_polygon(points, radius, steps=14):
    """Sample a polygon whose corners are rounded by `radius` (quadratic Bezier)."""
    n = len(points)
    out = []
    for i in range(n):
        p0, p1, p2 = points[i - 1], points[i], points[(i + 1) % n]
        dx1, dy1 = _unit(p0[0] - p1[0], p0[1] - p1[1])
        dx2, dy2 = _unit(p2[0] - p1[0], p2[1] - p1[1])
        t1 = (p1[0] + dx1 * radius, p1[1] + dy1 * radius)
        t2 = (p1[0] + dx2 * radius, p1[1] + dy2 * radius)
        for k in range(steps + 1):
            t = k / steps
            x = (1 - t) ** 2 * t1[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * t2[0]
            y = (1 - t) ** 2 * t1[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * t2[1]
            out.append((x, y))
    return out


def vertical_gradient(size, top, bottom):
    strip = Image.new("RGB", (1, 64))
    px = strip.load()
    for y in range(64):
        t = y / 63
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return strip.resize((size, size), Image.BICUBIC)


def radial_glow(size, center, radius, alpha):
    """Soft circular highlight built from concentric discs, then blurred."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    steps = 48
    for i in range(steps):
        t = i / (steps - 1)
        r = radius * (1 - t)
        draw.ellipse(
            [center[0] - r, center[1] - r, center[0] + r, center[1] + r],
            fill=int(alpha * (t ** 1.6)),
        )
    return mask.filter(ImageFilter.GaussianBlur(radius * 0.12))


def squircle_mask(size, margin, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=radius,
        fill=255,
    )
    return mask


def base_tile(size, margin_ratio=0.02, radius_ratio=0.235):
    """Filled rounded square: gradient, top-left highlight, rim light."""
    margin = round(size * margin_ratio)
    radius = round(size * radius_ratio)
    tile = vertical_gradient(size, TOP, BOTTOM).convert("RGBA")

    glow = radial_glow(size, (size * 0.32, size * 0.14), size * 0.66, 68)
    tile = Image.composite(Image.new("RGBA", (size, size), WHITE + (255,)), tile, glow)

    edge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle(
        [margin + size * 0.003, margin + size * 0.003, size - margin, size - margin],
        radius=radius,
        outline=(255, 255, 255, 52),
        width=max(2, round(size * 0.007)),
    )
    tile = Image.alpha_composite(tile, edge)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(tile, (0, 0), squircle_mask(size, margin, radius))
    return out


# DB-9 shell: wide at the top, tapering down, like the real connector flange.
SHIELD_OUTER = [(196, 344), (828, 344), (748, 700), (276, 700)]
SHIELD_INNER = [(250, 394), (774, 394), (700, 652), (324, 652)]
PINS_TOP = [(302 + i * 105, 452) for i in range(5)]
PINS_BOTTOM = [(378 + i * 91, 592) for i in range(4)]


def _scale_about(points, factor, centre=(512, 522)):
    """Grow/shrink a point set around `centre` (used for the small-size variant)."""
    cx, cy = centre
    return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in points]


def _shield_points(size, simplified=False):
    s = size / MASTER
    outer_pts, inner_pts = SHIELD_OUTER, SHIELD_INNER
    if simplified:
        # Below 24 px the nine pin holes collapse into noise and the shell
        # shrinks into the tile, so the small sizes get a bolder silhouette:
        # a bigger shell with a plain recessed face and no pins.
        outer_pts = _scale_about(outer_pts, 1.12)
        inner_pts = _scale_about(inner_pts, 1.12)
    return (
        _scaled(rounded_polygon(outer_pts, 52), s),
        _scaled(rounded_polygon(inner_pts, 30), s),
    )


def variant_a(size, simplified=False):
    """DB-9 connector: white shell, dark face, nine pin holes."""
    tile = base_tile(size)
    s = size / MASTER
    outer, inner = _shield_points(size, simplified)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon(
        [(x, y + 16 * s) for x, y in outer], fill=(4, 18, 48, 90)
    )
    tile = Image.alpha_composite(tile, shadow.filter(ImageFilter.GaussianBlur(20 * s)))

    # Shell filled with a near-white gradient so it reads as satin metal rather
    # than a flat cut-out.
    shell_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(shell_mask).polygon(outer, fill=255)
    shell = vertical_gradient(size, (255, 255, 255), (223, 234, 250)).convert("RGBA")
    tile = Image.composite(shell, tile, shell_mask)

    draw = ImageDraw.Draw(tile)
    draw.polygon(inner, fill=FACE)

    if not simplified:
        r = 20 * s
        for x, y in PINS_TOP + PINS_BOTTOM:
            cx, cy = x * s, y * s
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
    return tile


def variant_c(size, simplified=False):
    """Console window: dark panel, prompt caret, blinking-style cursor bar."""
    tile = base_tile(size)
    s = size / MASTER
    draw = ImageDraw.Draw(tile)

    panel = [(212, 318), (812, 318), (812, 706), (212, 706)]
    if simplified:
        panel = _scale_about(panel, 1.1)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon(
        [(x, y + 16 * s) for x, y in _scaled(rounded_polygon(panel, 64), s)],
        fill=(4, 18, 48, 90),
    )
    tile = Image.alpha_composite(tile, shadow.filter(ImageFilter.GaussianBlur(20 * s)))
    draw = ImageDraw.Draw(tile)

    draw.polygon(_scaled(rounded_polygon(panel, 64), s), fill=(18, 20, 26))
    w = max(2, round(34 * s))
    draw.line(_scaled([(330, 442), (452, 512), (330, 582)], s), fill=WHITE, width=w, joint="curve")
    draw.line(_scaled([(498, 582), (664, 582)], s), fill=(48, 190, 255), width=w)
    return tile


VARIANTS = {"a": variant_a, "c": variant_c}
# Sizes at or below this get the simplified silhouette (see _shield_points).
SMALL_CUTOFF = 24


def build_master(variant: str, simplified: bool = False) -> Image.Image:
    return VARIANTS[variant](MASTER * SS, simplified).resize((MASTER, MASTER), Image.LANCZOS)


def render(size: int, master: Image.Image, small: Image.Image | None = None) -> Image.Image:
    source = small if (small is not None and size <= SMALL_CUTOFF) else master
    img = source.resize((size, size), Image.LANCZOS)
    if size <= 40:
        # Sub-pixel detail turns to mush otherwise; a light unsharp pass keeps
        # the silhouette readable in the taskbar and window title.
        img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=55, threshold=0))
    return img


ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def write_ico(path: Path, frames: dict[int, Image.Image]) -> None:
    """Assemble an ICO from per-size PNG frames.

    Pillow's own ICO writer can only thumbnail one base image, which is exactly
    what we must avoid: the 16 px frame needs the simplified drawing, not a
    shrunk copy of the 256 px one. PNG frames are understood by Windows Vista+.
    """
    blobs = []
    for size in sorted(frames):
        buf = io.BytesIO()
        frames[size].save(buf, "PNG", optimize=True)
        blobs.append(buf.getvalue())

    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    entries = b""
    for size, blob in zip(sorted(frames), blobs):
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(header + entries + b"".join(blobs))


def write_assets(variant: str) -> None:
    master = build_master(variant)
    small = build_master(variant, simplified=True)
    master.resize((512, 512), Image.LANCZOS).save(ROOT / "icon.png")
    write_ico(ROOT / "icon.ico", {s: render(s, master, small) for s in ICO_SIZES})
    print(f"variant {variant}: icon.png 512x512, icon.ico {ICO_SIZES}")


def write_preview() -> None:
    """Contact sheet: each candidate large, then 64 / 32 / 16 px (nearest, x3)."""
    rows = []
    for name in VARIANTS:
        master = build_master(name)
        small = build_master(name, simplified=True)
        row = Image.new("RGBA", (620, 300), (245, 245, 245, 255))
        row.alpha_composite(render(256, master), (20, 22))
        x = 310
        for size in (64, 32, 16):
            img = render(size, master, small).resize((size * 3, size * 3), Image.NEAREST)
            row.alpha_composite(img, (x, 150 - size * 3 // 2 + 15))
            x += size * 3 + 18
        rows.append(row)

    sheet = Image.new("RGBA", (620, sum(r.height for r in rows)), (245, 245, 245, 255))
    y = 0
    for r in rows:
        sheet.alpha_composite(r, (0, y))
        y += r.height
    out = ROOT / ".user" / "icon-candidates.png"
    sheet.save(out)
    print(f"preview -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="a", choices=sorted(VARIANTS))
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    if args.preview:
        write_preview()
    else:
        write_assets(args.variant)
