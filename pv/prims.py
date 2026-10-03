"""Building blocks, same semantics as the reference PV's continuity_full_v2/kit.py.

The reference file loads continuity_full_v1 at import time; this build cannot (that tree is not
shipped here), so the primitives are re-expressed against the same contract:

  - every frame is composited in one fixed order (scene -> carriers as ink -> subject -> chrome -> CRT)
  - a transition is a function from screen position to switch time, never an artist's hand-drawn wipe
  - 'per-cell glyph switch from a seed, never a band wipe'

Nothing here draws a scene; it only moves, masks and keys.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import tuikit as tk

W, H = 1280, 720
PANE = (405, 44, 1164, 604)      # the visualisation pane with its title row
GLYPHS = "01<>/\\|=+*#%&$?!:;{}[]~^"

BG_AT = None                     # injected: BG_AT(t) -> RGB Image of the stage background, for ink()


def clamp(u: float) -> float:
    return max(0.0, min(1.0, u))


def ease_io(u: float) -> float:
    u = clamp(u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def ease_out(u: float) -> float:
    return 1 - (1 - clamp(u)) ** 3


def ease_in(u: float) -> float:
    return clamp(u) ** 3


def ease_back(u: float, s: float = 1.2) -> float:
    u = clamp(u) - 1
    return 1 + (s + 1) * u ** 3 + s * u ** 2


def lerp(a, b, u):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


def bezier(p0, p1, bend: float, u: float):
    """Quadratic arc from p0 to p1; bend > 0 bows to the left of the direction of travel."""
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    cx, cy = mx + dy * bend, my - dx * bend
    a, b, c = (1 - u) ** 2, 2 * (1 - u) * u, u * u
    return a * p0[0] + b * cx + c * p1[0], a * p0[1] + b * cy + c * p1[1]


# ---------------------------------------------------------------- ink and sprites

def ink(img: Image.Image, t: float, rect, floor: int = 12, gain: int = 5) -> Image.Image:
    """The drawn strokes inside rect as RGBA: the stage background is keyed out."""
    rect = tuple(int(v) for v in rect)
    crop = img.crop(rect).convert("RGB")
    bg = (BG_AT(t) if BG_AT else Image.new("RGB", img.size, tk.BG)).crop(rect)
    r, g, b = ImageChops.difference(crop, bg).split()
    a = ImageChops.lighter(ImageChops.lighter(r, g), b).point(
        lambda v: 0 if v < floor else min(255, (v - floor) * gain))
    out = crop.convert("RGBA")
    out.putalpha(a)
    return out


@lru_cache(1024)
def text_sprite(s: str, path: str, size: int, color: tuple) -> tuple[Image.Image, tuple[int, int]]:
    f = tk.font(path, size)
    l, tp, r, b = f.getbbox(s)
    im = Image.new("RGBA", (max(1, r - l + 6), max(1, b - tp + 6)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((3 - l, 3 - tp), s, font=f, fill=color)
    return im, (l - 3, tp - 3)


def haloed(sp: Image.Image, k: float, color=None, radius: int = 5) -> Image.Image:
    """Sprite with a soft coloured halo behind it (the 'selected' state of a carrier)."""
    if k <= 0.01:
        return sp
    pad = radius * 2
    out = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", out.size, 0)
    a.paste(sp.getchannel("A"), (pad, pad))
    a = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * 2.2 * k)))
    halo = Image.new("RGBA", out.size, (color or tk.blue(1.0)) + (0,))
    halo.putalpha(a)
    out.alpha_composite(halo)
    out.alpha_composite(sp, (pad, pad))
    return out


def brighten(sp: Image.Image, k: float, to=(235, 240, 255)) -> Image.Image:
    if k <= 0.01:
        return sp
    top = Image.new("RGBA", sp.size, to + (0,))
    top.putalpha(sp.getchannel("A").point(lambda v: int(v * clamp(k))))
    out = sp.copy()
    out.alpha_composite(top)
    return out


def place(layer: Image.Image, sp: Image.Image, center, scale: float = 1.0, alpha: float = 1.0) -> None:
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.01:
        sp = sp.resize((max(1, round(sp.width * scale)), max(1, round(sp.height * scale))), Image.LANCZOS)
    if alpha < 0.999:
        sp = tk.scale_alpha(sp, alpha)
    layer.alpha_composite(sp, (round(center[0] - sp.width / 2), round(center[1] - sp.height / 2)))


def blank() -> Image.Image:
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


# ---------------------------------------------------------------- per-cell glyph switch

def reveal(old: Image.Image, new: Image.Image, t: float, delay, region=PANE, cell=(8, 16), dur: float = 0.09,
           front: bool = True, seed: int = 0, density: float = 0.4) -> Image.Image:
    """Each cell of `region` switches from old to new when its own time comes: delay(cx, cy) gives that
    time (seconds on the same clock as t). While it switches, a cell that holds ink shows a decoding glyph."""
    x0, y0, x1, y1 = region
    cw, ch = cell
    cols, rows = (x1 - x0) // cw, (y1 - y0) // ch
    rw, rh = cols * cw, rows * ch
    box_ = (x0, y0, x0 + rw, y0 + rh)
    m = Image.new("L", (cols, rows), 0)
    mp = m.load()
    ps = []
    for r in range(rows):
        cy = y0 + r * ch + ch / 2
        for q in range(cols):
            cx = x0 + q * cw + cw / 2
            p = clamp((t - delay(cx, cy)) / dur)
            mp[q, r] = int(255 * p)
            if 0.02 < p < 0.98:
                ps.append((q, r, p))
    if not ps:
        lo, hi = m.getextrema()
        if hi == 0:
            return old.copy()
        if lo == 255:
            out = old.copy()
            out.paste(new.crop(box_), box_[:2])
            return out
    out = old.copy()
    mask = m.resize((rw, rh), Image.NEAREST)
    out.paste(Image.composite(new.crop(box_), old.crop(box_), mask), box_[:2])
    if front and ps:
        bg = (BG_AT(t) if BG_AT else Image.new("RGB", old.size, tk.BG)).crop(box_)
        inks = []
        for im in (old, new):
            r_, g_, b_ = ImageChops.difference(im.crop(box_).convert("RGB"), bg).split()
            lv = ImageChops.lighter(ImageChops.lighter(r_, g_), b_).resize((cols, rows), Image.BOX)
            inks.append(lv.load())
        d = ImageDraw.Draw(out)
        f = tk.font(tk.F_MONO_B, 13)
        rng = random.Random(seed * 9973 + int(t * 24))
        for q, r, p in ps:
            ch_ = rng.choice(GLYPHS)
            if inks[0][q, r] < 6 and inks[1][q, r] < 6 or rng.random() > density:
                continue
            k = 1 - abs(2 * p - 1)
            d.text((x0 + q * cw, y0 + r * ch), ch_, font=f, fill=tk.blue(0.2 + 0.6 * k))
    return out


def radial(seed, t0: float, speed: float):
    sx, sy = seed
    return lambda x, y: t0 + math.hypot(x - sx, y - sy) / speed


def inward(seed, t0: float, t1: float, reach: float = 900.0):
    """Cells far from `seed` go first, the seed itself last: the drawing drains into one point."""
    sx, sy = seed
    return lambda x, y: t1 - (t1 - t0) * min(1.0, math.hypot(x - sx, y - sy) / reach)


def sweep(origin, direction, t0: float, speed: float):
    ox, oy = origin
    dx, dy = direction
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    return lambda x, y: t0 + max(0.0, (x - ox) * dx + (y - oy) * dy) / speed


# ---------------------------------------------------------------- luminance -> terminal tile

def lum_tile(lum: Image.Image, px: int = 3, tint: str = "amber", grid: bool = True) -> Image.Image:
    """A greyscale drawing as a quantised, grid-masked, single-colour tile. The reference PV's
    'halfblock' look, but fed from a drawing instead of a sprite sheet."""
    size = (lum.width * px, lum.height * px)
    big = lum.resize(size, Image.NEAREST)
    a = big.point(lambda v: 255 if v > 16 else 0)
    if grid:
        a = ImageChops.multiply(a, tk.grid_mask(size[0], size[1], px))
    rgb = tk.tint_colorize(big, tint).convert("RGBA")
    rgb.putalpha(a)
    return rgb
