"""Scene library: the element layers, and the staging grammar that composes them.

Discipline (from the reference PV):
  - a shot declares (grammar, [elements], params) and never says how anything is drawn
  - "what to draw" and "how to move" stay separate: elements draw, the grammar places
  - nothing here touches chrome or post; the engine draws those once, last, untransformed

The subject is 东方红一号. She spins at 120 r/min, which at 24 fps is exactly 30 degrees a frame,
so her drawing has exactly twelve cached phases and the render is a pure function of t index.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import bigscene as bs
import chinamap as cm
import facts as F
import icons as ic
import prims as pk
import pvclock as ck
import tuikit as tk

W, H = 1280, 720
LEFT = (24, 56, 384, 604)          # the subject pane
CENTER = (404, 56, 1164, 604)      # the visualisation pane
FULL = (24, 56, 1164, 604)
TICK = (1180, 56, 1256, 604)

PHASES = 12                        # 120 rpm / 60 * 24 fps = 48 rev/min... see note below

# 120 r/min = 2 rev/s = 720 deg/s = 30 deg/frame at 24 fps -> twelve distinct phases.
assert abs((F.SPIN_RPM / 60.0) * 24 % 12) < 1e-9, "spin no longer lands on twelve phases"


# ---------------------------------------------------------------- context

class Ctx:
    def __init__(self, img: Image.Image, t: float, lt: float, dur: float, rng: random.Random,
                 chapter: str = "", ui: float = 1.0, alert: str = "", params: dict | None = None):
        self.img = img
        self._d = ImageDraw.Draw(img)
        self.t = t
        self.lt = lt
        self.dur = dur
        self.rng = rng
        self.chapter = chapter
        self.ui = ui
        self.alert = alert
        self.params = params or {}
        self.ops: list[str] = []
        self.echo = ""
        self.here = True           # the subject pane is wanted in this shot

    @property
    def d(self) -> ImageDraw.ImageDraw:
        return self._d

    @property
    def u(self) -> float:
        return pk.clamp(self.lt / max(1e-6, self.dur))

    def text(self, xy, s, f, fill, age=None, rate=60.0):
        """age=None draws the whole string at once. age >= 0 draws it *being typed* at `rate`
        characters a second -- every proof shot in the reference film is typed, and a typed line
        reads as something being worked out rather than as a caption that was always there."""
        if age is None:
            self._d.text(xy, s, font=f, fill=fill)
            return
        n = max(0, min(len(s), int(age * rate)))
        if n:
            self._d.text(xy, s[:n], font=f, fill=fill)

    def box(self, rect, title="", level=0.5, color=None, spinner=None):
        tk.box(self._d, rect[0], rect[1], rect[2], rect[3], title, level, color or tk.UI, spinner)


# ---------------------------------------------------------------- the subject: 东方红一号

@lru_cache(24)
def _sphere(w: int, r_q: int = 44) -> Image.Image:
    """Aluminium sphere with a terminator and an edge lift. Luminance only, cached once."""
    r = w * r_q / 100.0
    cx = cy = w / 2.0
    yy, xx = np.mgrid[0:w, 0:w].astype(np.float32)
    dx, dy = (xx - cx) / r, (yy - cy) / r
    r2 = dx * dx + dy * dy
    inside = r2 <= 1.0
    dz = np.sqrt(np.clip(1.0 - r2, 0.0, None))
    lx, ly = -0.55, -0.72
    lz = math.sqrt(1.0 - lx * lx - ly * ly)
    lam = np.clip(dx * lx + dy * ly + dz * lz, 0.0, None)
    val = 26.0 + 228.0 * lam ** 0.7
    edge = np.clip((r2 - 0.55) / 0.45, 0.0, 1.0) * 46.0          # rim light on the polished skin
    val = np.clip(val + edge * 0.5, 0, 255) * inside
    return Image.fromarray(val.astype(np.uint8), "L")


def sat_lum(w: int, phase: int, deploy: float = 1.0, r_q: int = 44) -> Image.Image:
    """The satellite as a luminance drawing. phase 0..11 spins the facet grid; deploy 0..1 furls the
    four whip antennas, which is exactly what the launch sequence needs."""
    im = _sphere(w, r_q).copy()
    d = ImageDraw.Draw(im)
    r = w * r_q / 100.0
    cx = cy = w / 2.0
    spin = phase / PHASES * 2 * math.pi
    dark = 12
    for k in range(6):                                  # six visible meridians of the 72-hedron
        phi = k * math.pi / 6 + spin
        pts = [(cx + r * math.sin(th) * math.cos(phi), cy - r * math.cos(th))
               for th in np.linspace(0, math.pi, 26)]
        d.line(pts, fill=dark, width=max(1, w // 90))
    for k in range(1, 6):                               # parallels: horizontal chords
        th = k * math.pi / 6
        yy = cy - r * math.cos(th)
        hw = r * math.sin(th)
        d.line([cx - hw, yy, cx + hw, yy], fill=dark, width=max(1, w // 90))
    # one lit marker riding the equator so the spin is legible
    mk = cx + r * 0.82 * math.cos(spin + 0.6)
    my = cy - r * 0.16
    d.ellipse([mk - w / 60, my - w / 60, mk + w / 60, my + w / 60], fill=230)
    # four whip antennas, from under the equator
    L = r * 1.75 * deploy
    for i in range(4):
        a = math.radians(52 + i * 66)
        x0, y0 = cx + r * 0.42 * math.cos(a), cy + r * 0.62
        x1, y1 = x0 + L * math.cos(a) * 0.55, y0 + L * math.sin(a) * 0.72
        d.line([x0, y0, x1, y1], fill=200 if i % 2 == 0 else 150, width=max(1, w // 70))
        d.ellipse([x1 - w / 70, y1 - w / 70, x1 + w / 70, y1 + w / 70], fill=235)
    return im


def draw_sat(c: Ctx, center, size_px: int, phase: int, tint: str = "amber", deploy: float = 1.0, px: int = 2):
    w = max(16, int(size_px / px))
    sp = pk.lum_tile(sat_lum(w, phase % PHASES, round(deploy * 10) / 10), px, tint)
    c.img.paste(sp, (int(center[0] - sp.width / 2), int(center[1] - sp.height / 2)), sp)


def spin_phase(t: float) -> int:
    """120 r/min = 2 rev/s; at 24 fps that is 24 phases a second, i.e. one of twelve each frame."""
    return int(t * (F.SPIN_RPM / 60.0) * PHASES) % PHASES


# ---------------------------------------------------------------- elements
# every element draws inside rect and returns nothing

def _T(rect, u, v):
    x0, y0, x1, y1 = rect
    return x0 + (x1 - x0) * u, y0 + (y1 - y0) * v


def el_her(c: Ctx, rect, **kw):
    """The subject pane: her frame, her drawing, her readouts, and one scan line."""
    x0, y0, x1, y1 = rect
    box = (x0 + 6, y0 + 22, x1 - 6, y1 - 8)
    c.box(rect, kw.get("title", "/dev/dfh-1  1970-034A"), (0.45 + 0.3 * ck.pulse(c.t)), spinner=c.t)
    t = c.t
    lit = kw.get("lit", 1.0)
    phase = spin_phase(t)
    size = int(min(box[2] - box[0], box[3] - box[1]) * 0.62 * kw.get("zoom", 1.0))
    cx = (box[0] + box[2]) / 2
    cy = box[1] + (box[3] - box[1]) * 0.40
    draw_sat(c, (cx, cy), size, phase, "amber", kw.get("deploy", 1.0))
    # readouts: spin / bus volts / skin temp / tune level -- the first three are facts
    f = tk.font(tk.F_MONO, 12)
    fh = tk.font(tk.F_CJK, 15)
    rows = [
        ("spin", f"{F.SPIN_RPM:>4d} r/min"),
        ("volt", f"{kw.get('volt', 27.3 + 0.4 * math.sin(t * 1.7)):>6.2f} V"),
        ("temp", f"{kw.get('temp', 14 + 9 * math.sin(t * 0.21 + 1)):>6.1f} C"),
        ("tune", f"{kw.get('tune', 0.4 + 0.5 * ck.pulse(t)):>6.2f}"),
    ]
    yy = box[3] - len(rows) * 17 - 26
    for k, v in rows:
        c.text((box[0] + 8, yy), f"{k:<5}{v}", f, tk.amb(0.55 * lit))
        yy += 17
    c.text((box[0] + 8, box[3] - 24), "东方红一号" if kw.get("cjk", True) else "DFH-1", fh,
           tk.amb(0.85 * lit))
    # the scan line only inside her silhouette: a 6 px bright band that sweeps
    sy = box[1] + (box[3] - box[1]) * (0.5 + 0.5 * math.sin(t * 0.9))
    c.d.line([box[0] + 10, sy, box[2] - 10, sy], fill=tk.amb(0.32 * lit), width=1)
    c.d.line([box[0] + 10, sy + 1, box[2] - 10, sy + 1], fill=tk.amb(0.14 * lit), width=1)


def el_orbit(c: Ctx, rect, **kw):
    """The ellipse, the Earth at one focus, her dot riding it, and the two radius marks (facts)."""
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a = (x1 - x0) * 0.40
    b = (y1 - y0) * 0.30
    ecc = 0.36
    ox = cx - a * ecc
    c.d.ellipse([ox - a, cy - b, ox + a, cy + b], outline=tk.amb(0.5), width=1)
    # earth at the focus, drawn as a half-block disc
    er = 16
    for yy in range(-er, er + 1):
        hw = int(math.sqrt(max(0, er * er - yy * yy)))
        shade = 0.35 + 0.5 * (1 - abs(yy) / er)
        c.d.line([cx + ecc * a - hw, cy + yy, cx + ecc * a + hw, cy + yy], fill=tk.amb(shade * 0.5))
    c.text((cx + ecc * a - 26, cy + er + 4), "EARTH", tk.font(tk.F_MONO, 11), tk.amb(0.45))
    # her position on the ellipse
    ph = kw.get("phase", (c.t / (F.PERIOD_MIN * 60)) % 1.0)
    ang = ph * 2 * math.pi
    px = ox + a * math.cos(ang)
    py = cy + b * math.sin(ang)
    c.d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=tk.amb(1.0))
    c.d.ellipse([px - 7, py - 7, px + 7, py + 7], outline=tk.amb(0.3))
    # the facts, printed where an operator would look for them
    f = tk.font(tk.F_MONO, 12)
    c.text((x0 + 10, y0 + 8), f"perigee  {F.PERIGEE_KM} km", f, tk.amb(0.6))
    c.text((x0 + 10, y0 + 24), f"apogee   {F.APOGEE_KM} km", f, tk.amb(0.6))
    c.text((x0 + 10, y0 + 40), f"incl     {F.INCL_DEG} deg", f, tk.amb(0.6))
    c.text((x0 + 10, y0 + 56), f"period   {F.PERIOD_MIN} min", f, tk.amb(0.6))
    return (px, py)


def el_spectrum(c: Ctx, rect, **kw):
    """A waterfall around 20.009 MHz. The carrier is a fact; the noise is decoration."""
    x0, y0, x1, y1 = rect
    f = tk.font(tk.F_MONO, 11)
    c.text((x0 + 8, y0 + 6), kw.get("label", "SHORTWAVE  19.5 - 20.6 MHz"), tk.font(tk.F_CJK, 12),
           tk.amb(0.55))
    top = y0 + 26
    rows = 26
    cols = 92
    cw = (x1 - x0 - 20) / cols
    ch = (y1 - top - 26) / rows
    rng = random.Random(int(c.t * 6))
    peak_col = int(cols * (F.FREQ_MHZ - 19.5) / 1.1)
    for r in range(rows):
        age = r / rows
        for q in range(cols):
            v = rng.random() * 0.22
            if abs(q - peak_col) <= 1:
                v = max(v, (1.0 - age) * (0.75 + 0.25 * ck.pulse(c.t)))
            elif abs(q - peak_col) <= 4:
                v = max(v, (1.0 - age) * 0.28 * rng.random())
            if v < 0.06:
                continue
            tk.heat_cell(c.d, x0 + 10 + q * cw, top + r * ch, cw, ch, v, tk.UI)
    c.d.line([x0 + 10 + peak_col * cw, top, x0 + 10 + peak_col * cw, y1 - 26], fill=tk.red(0.9), width=1)
    c.text((x0 + 10 + peak_col * cw - 22, y1 - 22), f"{F.FREQ_MHZ}", tk.font(tk.F_MONO_B, 12), tk.red(0.95))
    c.text((x0 + 10, y1 - 22), "MHz", f, tk.amb(0.4))


# the first two bars of 东方红 as scale degrees (5 5 6 2 | 1 1 6 5), i.e. sol sol la re | do do la sol
TUNE_DEG = [5, 5, 6, 2, 1, 1, 6, 5]


def el_wave(c: Ctx, rect, **kw):
    """The tune as a step line, one note per beat, plus the oscillator that sang it (a fact)."""
    x0, y0, x1, y1 = rect
    f = tk.font(tk.F_MONO, 11)
    fc = tk.font(tk.F_CJK, 12)
    c.text((x0 + 8, y0 + 6), f"AUDIO OSCILLATOR  ·  {F.AUDIO_SRC}", fc, tk.amb(0.5))
    top, bot = y0 + 40, y1 - 34
    n = kw.get("notes", TUNE_DEG)
    span = x1 - x0 - 40
    step = span / max(1, len(n))
    lit = kw.get("lit", 1.0)
    prog = kw.get("progress", 1.0)
    prev = None
    for i, deg in enumerate(n):
        u = (i + 0.5) / len(n)
        if u > prog:
            break
        xx = x0 + 20 + i * step + step / 2
        yy = bot - (deg - 1) / 6 * (bot - top)
        if prev is not None:
            c.d.line([prev[0], prev[1], xx, prev[1]], fill=tk.amb(0.35 * lit))
            c.d.line([xx, prev[1], xx, yy], fill=tk.amb(0.35 * lit))
        c.d.ellipse([xx - 5, yy - 5, xx + 5, yy + 5], fill=tk.amb((0.55 + 0.45 * (0.5 + 0.5 * math.sin(c.t * 4 + i))) * lit))
        deg_f = tk.font(tk.F_MONO, 11)
        c.text((xx - 3, yy - 22), str(deg), deg_f, tk.amb(0.5 * lit))
        prev = (xx, yy)
    c.d.line([x0 + 20, bot + 8, x1 - 20, bot + 8], fill=tk.amb(0.2))
    c.text((x0 + 20, bot + 12), "1  2  3  4  5  6  7  8", f, tk.amb(0.3))
    return prev


def el_stars(c: Ctx, rect, **kw):
    """A star field with a slow track. Brightness is deterministic in t so the frame is reproducible."""
    x0, y0, x1, y1 = rect
    n = kw.get("n", 160)
    rng = random.Random(kw.get("seed", 7))
    for _ in range(n):
        sx = rng.randrange(int(x0), int(x1))
        sy = rng.randrange(int(y0), int(y1))
        base = rng.random()
        v = base * (0.55 + 0.45 * math.sin(c.t * (0.6 + base * 2.2) + base * 40))
        if v < 0.12:
            continue
        g = (235, 240, 255) if rng.random() < 0.25 else None
        c.d.point((sx, sy), fill=g and tuple(int(x * v) for x in g) or tk.amb(v * 0.9))
        if base > 0.9:
            c.d.point((sx + 1, sy), fill=tk.amb(v * 0.35))
            c.d.point((sx, sy + 1), fill=tk.amb(v * 0.35))


def el_grid(c: Ctx, rect, **kw):
    """A grid of cells, each filling in its own time: the 'lay down your pieces' primitive."""
    x0, y0, x1, y1 = rect
    cols = kw.get("cols", 16)
    rows = kw.get("rows", 9)
    cw, ch = (x1 - x0) / cols, (y1 - y0) / rows
    rng = random.Random(kw.get("seed", 3))
    u = kw.get("progress", c.u)
    for r in range(rows):
        for q in range(cols):
            order = rng.random()
            if order > u:
                if order < u + 0.06:
                    c.d.rectangle([x0 + q * cw, y0 + r * ch, x0 + (q + 1) * cw - 2, y0 + (r + 1) * ch - 2],
                                  outline=tk.amb(0.22))
                continue
            v = 0.18 + 0.5 * rng.random()
            tk.heat_cell(c.d, x0 + q * cw, y0 + r * ch, cw, ch, v, tk.UI)
    c.d.rectangle([x0, y0, x1, y1], outline=tk.amb(0.3))


def _face(s, mono: int = 13, cjk: int = 14):
    """Pick the face per string: the mono face has no CJK glyphs and renders them as boxes.

    One face for the whole string is right for a cell that is all one script. Where the string mixes
    the two -- a date followed by a Chinese label -- use tk.mixed_text, which swaps face per run."""
    return tk.font(tk.F_CJK, cjk) if any(tk.needs_cjk(ch) for ch in str(s)) else tk.font(tk.F_MONO, mono)


def el_table(c: Ctx, rect, rows, **kw):
    """A two-column parameter table. Every value here is from facts.py."""
    x0, y0, x1, y1 = rect
    c.text((x0 + 10, y0 + 8), kw.get("title", "PARAMETERS"), tk.font(tk.F_CJK, 15), tk.amb(0.6))
    yy = y0 + 40
    step = min(22, (y1 - yy - 10) / max(1, len(rows)))
    for k, v in rows:
        c.text((x0 + 12, yy), str(k), _face(k), tk.amb(0.55))
        # a value like "1970-04-24 21:35  点火" is two scripts on one line; per-run faces keep the
        # figures mono and the label readable
        tk.mixed_text(c.d, (x0 + 12 + (x1 - x0) * 0.46, yy), str(v), tk.amb(0.85), size=14)
        c.d.line([x0 + 12, yy + step - 5, x1 - 12, yy + step - 5], fill=tk.amb(0.1))
        yy += step


def el_log(c: Ctx, rect, lines, **kw):
    """A scrolling log. Lines appear on the grid and settle like a real console. The face is the CJK
    one because the archive lines mix Chinese and Latin; a real console would do the same."""
    x0, y0, x1, y1 = rect
    f = tk.font(tk.F_CJK, 14)
    speed = kw.get("speed", 12.0)
    rows = int((y1 - y0 - 30) / 18)
    shown = int(max(0, c.lt) * speed)
    start = max(0, len(lines) - rows)
    for i in range(start, min(len(lines), start + rows)):
        age = min(1.0, max(0.0, (shown - (i - start)) / 6.0))
        if age <= 0:
            continue
        col = tk.red(0.9) if lines[i].startswith("!") else tk.amb(0.35 + 0.55 * age)
        c.text((x0 + 10, y0 + 10 + (i - start) * 18), tk.decode(lines[i], age * 2.0, c.rng, 60.0, 0.1),
               f, col)


def el_beam(c: Ctx, rect, **kw):
    """A radio link: a carrier line with a travelling packet, plus the layer it crosses."""
    x0, y0, x1, y1 = rect
    y = (y0 + y1) / 2 + kw.get("dy", 0)
    c.d.line([x0 + 8, y, x1 - 8, y], fill=tk.amb(0.18))
    n = kw.get("packets", 5)
    for i in range(n):
        u = ((c.t * 0.55) + i / n) % 1.0
        xx = x0 + 8 + (x1 - 16) * u
        k = math.sin(u * math.pi)
        c.d.ellipse([xx - 3 - k * 3, y - 3 - k * 3, xx + 3 + k * 3, y + 3 + k * 3], fill=tk.amb(0.35 + 0.6 * k))
    if kw.get("layers"):
        for j, lab in enumerate(kw["layers"]):
            ly = y0 + (y1 - y0) * (j + 1) / (len(kw["layers"]) + 1)
            c.d.line([x0 + 8, ly, x1 - 8, ly], fill=tk.amb(0.1))
            # the layers are named in Chinese (电离层 F / 对流层 / 地面站) with the numerals in mono
            tk.mixed_text(c.d, (x1 - 8 - 60, ly - 14), lab, tk.amb(0.35), size=10)


def el_banner(c: Ctx, rect, text, **kw):
    """Big letters, drawn as blocks. Size is chosen so it always fits."""
    x0, y0, x1, y1 = rect
    target_h = kw.get("h", 0.5)
    rows = max(3, int((y1 - y0) * target_h / 6))
    sp = tk.banner_block(text, rows, 6, tk.amb(1.0), tk.BG, max_w=x1 - x0 - 40)
    k = kw.get("scale", 1.0)
    if k != 1.0:
        sp = sp.resize((max(1, int(sp.width * k)), max(1, int(sp.height * k))), Image.LANCZOS)
    alpha = kw.get("alpha", 1.0)
    if alpha < 0.999:
        sp = tk.scale_alpha(sp, alpha)
    c.img.paste(sp, (int((x0 + x1 - sp.width) / 2), int((y0 + y1 - sp.height) / 2)), sp)


def el_timeline(c: Ctx, rect, **kw):
    """Two decades on one line, with the wire between them: the 'half a century' shot."""
    x0, y0, x1, y1 = rect
    y = (y0 + y1) / 2 + kw.get("dy", 0)
    f = tk.font(tk.F_MONO, 12)
    fh = tk.font(tk.F_CJK, 14)
    c.d.line([x0 + 10, y, x1 - 10, y], fill=tk.amb(0.35))
    marks = kw.get("marks", [(0.10, "1970.04.24"), (0.30, "1970.05.14"), (0.62, "2009"), (0.90, "2026")])
    for u, lab in marks:
        xx = x0 + 10 + (x1 - 20) * u
        c.d.line([xx, y - 8, xx, y + 8], fill=tk.amb(0.8))
        c.text((xx - len(lab) * 3.2, y + 12), lab, f, tk.amb(0.6))
    cur = x0 + 10 + (x1 - 20) * kw.get("now", 0.9)
    c.d.ellipse([cur - 4, y - 4, cur + 4, y + 4], fill=tk.red(0.95))
    c.text((x0 + 10, y - 34), kw.get("left", "1970"), fh, tk.amb(0.6))
    c.text((x1 - 60, y - 34), kw.get("right", "今天"), fh, tk.red(0.7))
    return y


def el_gauge(c: Ctx, rect, label, value, unit, lo=0.0, hi=1.0, **kw):
    """A horizontal meter."""
    x0, y0, x1, y1 = rect
    f = tk.font(tk.F_MONO, 12)
    c.text((x0, y0 - 16), f"{label}", f, tk.amb(0.55))
    c.text((x1 - 70, y0 - 16), f"{value}{unit}", f, tk.amb(0.85))
    c.d.rectangle([x0, y0, x1, y1], outline=tk.amb(0.35))
    u = pk.clamp((kw.get("frac", 0.5) - lo) / max(1e-6, hi - lo))
    c.d.rectangle([x0 + 1, y0 + 1, x0 + 1 + (x1 - x0 - 2) * u, y1 - 1], fill=tk.amb(0.6))
    for i in range(1, 5):
        xx = x0 + (x1 - x0) * i / 5
        c.d.line([xx, y1, xx, y1 + 4], fill=tk.amb(0.3))


def el_rocket(c: Ctx, rect, **kw):
    """The vehicle on its gantry: three stages, 29.46 m, and the tower beside it.

    `lift` (0..1) is how far the stack has climbed out of the pane. The gantry does not move, which
    is what makes the climb legible: the tower stays and the rocket does not. Either `ignited` or
    `lift` may be given as the string "auto", in which case the frame reads it off the shot's own
    clock (c.u) and a launch becomes an animation rather than two stills.

    Everything the vehicle draws goes into a copy of the pane which is pasted back at the end. That
    is deliberate, and it is the fix for a real defect: the plume used to be drawn straight onto the
    frame, ran off the bottom of the pane and into the lyric band, and made the subtitle
    unreadable. The same crop is what keeps the nose inside the window once the stack climbs -- the
    nose cone used to be able to walk up through the header."""
    x0, y0, x1, y1 = (int(v) for v in rect)
    u = c.u
    ignited = kw.get("ignited", 0.0)
    lift = kw.get("lift", 0.0)
    if isinstance(ignited, str):
        ignited = pk.clamp((u - 0.06) / 0.30)
    if isinstance(lift, str):
        lift = pk.clamp((u - 0.16) / 0.68)

    sub = c.img.crop((x0, y0, x1, y1))
    d = ImageDraw.Draw(sub)
    pw, ph = x1 - x0, y1 - y0

    cx = pw / 2 - pw * 0.12
    gy = ph * 0.80                                   # the pad, which never moves
    climb = lift * ph * float(kw.get("climb", 0.46))
    bot = gy - ph * 0.02 - climb
    top = bot - ph * 0.58
    hgt = bot - top
    wdt = hgt * (F.ROCKET_DIA_M / F.ROCKET_LEN_M) * 3.0
    # the stick, three stages
    for i, frac in enumerate((0.0, 0.30, 0.68)):
        y_a = top + hgt * frac
        y_b = top + hgt * (0.30 if i == 0 else 0.68 if i == 1 else 1.0)
        w_here = wdt * (1.0 if i < 2 else 0.8)
        d.rectangle([cx - w_here / 2, y_a, cx + w_here / 2, y_b], outline=tk.amb(0.55))
        d.line([cx - w_here / 2, y_b, cx + w_here / 2, y_b], fill=tk.amb(0.35))
    d.polygon([(cx - wdt / 2, top), (cx + wdt / 2, top), (cx, top - wdt * 0.9)], outline=tk.amb(0.6))
    # gantry: fixed to the ground, and left standing once the stack moves
    gx = cx + pw * 0.26
    d.rectangle([gx - 9, ph * 0.06, gx + 9, gy + ph * 0.04], outline=tk.amb(0.35))
    for k in range(9):
        yy = ph * (0.08 + k * 0.095)
        d.line([gx - 9, yy, cx + wdt / 2, yy + 3], fill=tk.amb(0.18))
    # the ground, and the smoke that stays on it: the one thing in a launch that does not move
    if kw.get("pad") or lift > 0.01:
        d.line([0, gy, pw, gy], fill=tk.amb(0.30))
        for k in range(5):
            t = k / 4.0
            yy = gy - 2 + k * 6
            half = pw * (0.05 + 0.17 * t) * (0.45 + 0.55 * min(1.0, lift * 2.2))
            d.line([cx - half - 18 * t, yy, cx - 12 * (1 - t), yy], fill=tk.amb(0.26 - 0.040 * k))
            d.line([cx + 12 * (1 - t), yy, cx + half + 18 * t, yy], fill=tk.amb(0.26 - 0.040 * k))
    # flame: from the nozzle down, tapering to a point, and never leaving the pane. The crop would
    # cut it anyway; the cap keeps it from being cut, so the plume ends in a tip rather than on the
    # top edge of the subtitle.
    if ignited > 0.01:
        fl = min(hgt * 0.40 * ignited, (ph - bot) * 0.88)
        if fl > 1:
            # The plume is a stack of scanned lines in the palette's own amber -- white-hot at the
            # nozzle, dim at the tip -- and not the filled photographic-fire gradient it used to be.
            # That gradient (235,130,35) -> (255,255,200) was the one thing in the whole film drawn
            # in colours that appear nowhere else on any frame, which is exactly why it read as
            # pasted in from a different picture. Same language as the stick now: lines, not slabs.
            yy = bot
            while yy < bot + fl:
                t = min(1.0, (yy - bot) / fl)
                ww = wdt * (1.12 - 0.22 * t - t * t)
                d.line([cx - ww / 2, yy, cx + ww / 2, yy], fill=tk.hot(1.00 - 0.42 * t), width=3)
                cw = wdt * 0.42 * (1 - t)
                if cw > 1:
                    d.line([cx - cw / 2, yy, cx + cw / 2, yy], fill=tk.hot(1.00 - 0.18 * t), width=3)
                yy += 2
    c.img.paste(sub, (x0, y0))

    # F.ROCKET is "长征一号 / CZ-1": a Chinese name followed by an ASCII designation and the mass and
    # length. Set whole in the mono face the four ideographs came out as four empty boxes, and set
    # whole in the CJK face the figures lose the mono rhythm the rest of the pane is set in. Each run
    # gets its own face, on one baseline.
    tk.mixed_text(c.d, (x0 + 10, y0 + 6),
                  f"{F.ROCKET}  {F.ROCKET_LEN_M} m  {F.ROCKET_MASS_T} t", tk.amb(0.55), size=12)
    c.text((x0 + 10, y1 - 20), f"{F.SITE}", tk.font(tk.F_CJK, 13), tk.amb(0.6))
    return cx + x0, bot + y0


# ---------------------------------------------------------------- the map
# The Earth used to be a half-tone disc with a dot on it. A disc is what you draw when you do not
# know where you are; this film knows exactly where it is. So the disc is replaced by a real map of
# China, drawn from a national-standard boundary set (see chinamap.py) and rendered as the same
# colour blocks as everything else.

T_ORBIT = F.PERIOD_MIN * 60.0
SIDEREAL_D = 86164.0


def subpoint(t: float) -> tuple[float, float]:
    """The point on the ground she is above at song time t.

    For a circular orbit of inclination i: lat = asin(sin i * sin(2*pi*u)). Inertial longitude
    advances one turn per orbit while the Earth turns under it, so the earth-fixed longitude loses
    360*t/86164. The net effect is the familiar west-shifted family of tracks -- 28.6 degrees per
    orbit at this inclination and period, which is the real number, not a drawn-on effect.
    """
    u = t / T_ORBIT
    lat = math.degrees(math.asin(math.sin(math.radians(F.INCL_DEG)) * math.sin(2 * math.pi * u)))
    lon = F.SITE_LATLON[0] + 360.0 * u - 360.0 * t / SIDEREAL_D
    return ((lon + 180.0) % 360.0) - 180.0, lat


def _track(t: float, span: float = 1.6) -> list[list[tuple[float, float]]]:
    """The ground track as lon/lat polylines, split wherever it crosses the antimeridian."""
    out, cur = [], []
    n = 200
    for i in range(n + 1):
        tt = t - span * T_ORBIT + 2 * span * T_ORBIT * i / n
        lon, lat = subpoint(tt)
        if cur and abs(lon - cur[-1][0]) > 90:
            out.append(cur)
            cur = []
        cur.append((lon, lat))
    if cur:
        out.append(cur)
    return out


@lru_cache(64)
def _map_sprite(w: int, h: int, cell: int, tint: str, which: str) -> Image.Image:
    """A cached colour-block sprite of the map, at block resolution."""
    mask = cm.land_cells(w, h, cell) if which == "land" else cm.sea_cells(w, h, cell)
    cols, rows = mask.size
    big = mask.resize((cols * cell, rows * cell), Image.NEAREST)
    gut = Image.new("L", big.size, 255)
    d = ImageDraw.Draw(gut)
    if cell >= 3:
        for x in range(cell - 1, big.width, cell):
            d.line([x, 0, x, big.height], fill=0)
        for y in range(cell - 1, big.height, cell):
            d.line([0, y, big.width, y], fill=0)
    big = ImageChops.multiply(big, gut)
    rgb = tk.tint_colorize(big, tint).convert("RGBA")
    rgb.putalpha(big.point(lambda v: 0 if v < 8 else min(255, int(v * 1.3))))
    return rgb


def el_chinamap(c: Ctx, rect, **kw):
    """Complete, accurate China: 34 province-level units including 台湾; 海南; and the 南海诸岛 with
    the 九段线 in the standard inset. Launch site and ground stations marked. Everything cut from
    blocks, like the rest of the film."""
    x0, y0, x1, y1 = (int(v) for v in rect)
    w, h = x1 - x0, y1 - y0
    if w < 60 or h < 50:
        return None
    lit = kw.get("lit", 1.0)
    cell = int(kw.get("cell", 3))
    d = c.d

    if kw.get("grid", True):
        merid, par = cm.graticule(w, h, 10)
        for line in merid + par:
            d.line([(x0 + px, y0 + py) for px, py in line], fill=tk.amb(0.085 * lit))

    # the ground track, and where she is on it right now. Clipped to the frame: a track that is
    # allowed to run off the edge of the map stops reading as a track and starts reading as scribble.
    lon0, lat0, lon1, lat1 = cm.MAIN_BOX
    if kw.get("track", True):
        for seg in _track(c.t):
            cur = []
            for lo, la in seg:
                if lon0 <= lo <= lon1 and lat0 <= la <= lat1:
                    cur.append(cm.to_px(lo, la, w, h))
                else:
                    if len(cur) > 1:
                        d.line([(x0 + px, y0 + py) for px, py in cur], fill=tk.amb(0.34 * lit))
                    cur = []
            if len(cur) > 1:
                d.line([(x0 + px, y0 + py) for px, py in cur], fill=tk.amb(0.34 * lit))
        lon, lat = subpoint(c.t)
        if lon0 <= lon <= lon1 and lat0 <= lat <= lat1:
            px, py = cm.to_px(lon, lat, w, h)
            k = ck.pulse(c.t)
            d.ellipse([x0 + px - 7 - 4 * k, y0 + py - 7 - 4 * k, x0 + px + 7 + 4 * k, y0 + py + 7 + 4 * k],
                      outline=tk.red(0.35 * lit))
            d.ellipse([x0 + px - 3, y0 + py - 3, x0 + px + 3, y0 + py + 3], fill=tk.red(0.95 * lit))

    sp = _map_sprite(w, h, cell, "amber", "land")
    c.img.paste(sp, (x0, y0), sp)

    # 南海诸岛 inset, bottom-right, the way a published map carries it
    iw = int(kw.get("inset") or min(78, max(46, w * 0.30)))
    ih = int(iw * 1.24)
    ix, iy = x1 - iw - 4, y1 - ih - 4
    d.rectangle([ix - 2, iy - 2, ix + iw + 1, iy + ih + 1], fill=tk.BG, outline=tk.amb(0.4 * lit))
    ssp = _map_sprite(iw, ih, max(1, cell - 1), "amber", "sea")
    c.img.paste(ssp, (ix, iy), ssp)
    d.rectangle([ix - 2, iy - 2, ix + iw + 1, iy + ih + 1], outline=tk.amb(0.45 * lit))
    c.text((ix - 1, iy - 15), "南海诸岛", tk.font(tk.F_CJK, 11), tk.amb(0.5 * lit))

    # the places that matter
    for lon, lat, label, col in kw.get("marks", [(F.SITE_LATLON[0], F.SITE_LATLON[1], F.SITE, "red"),
                                                 (F.BEIJING_LATLON[0], F.BEIJING_LATLON[1], "北京", "amb")]):
        px, py = cm.to_px(lon, lat, w, h)
        if not (0 <= px <= w and 0 <= py <= h):
            continue
        col = tk.red(0.95) if col == "red" else tk.amb(0.8)
        d.rectangle([x0 + px - 2, y0 + py - 2, x0 + px + 2, y0 + py + 2], fill=col)
        c.text((x0 + px + 6, y0 + py - 7), label, tk.font(tk.F_CJK, 12), col)
    if kw.get("approval", True):
        c.text((x0 + 4, y1 - 14), "审图号 " + F.MAP_APPROVAL, tk.font(tk.F_CJK, 10),
               tk.amb(0.32 * lit))
    return x0, y0, w, h


def el_earth(c: Ctx, rect, **kw):
    """Kept as the name every shot already uses; it is the China map now, not a generic disc.
    `r` shrinks the map about the centre so the old r=0.34 / 0.40 / 0.42 calls keep their framing."""
    r = kw.get("r")
    if r:
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        kx, ky = r / 0.40, r / 0.40
        rect = (cx - (rect[2] - rect[0]) / 2 * kx, cy - (rect[3] - rect[1]) / 2 * ky,
                cx + (rect[2] - rect[0]) / 2 * kx, cy + (rect[3] - rect[1]) / 2 * ky)
    marks = kw.get("marks")
    if marks is None:
        marks = [(F.SITE_LATLON[0], F.SITE_LATLON[1], kw.get("slabel", F.SITE), "red")]
        if kw.get("station", True):
            marks.append((F.BEIJING_LATLON[0], F.BEIJING_LATLON[1], "北京", "amb"))
    return el_chinamap(c, rect, marks=marks, lit=kw.get("lit", 1.0), inset=kw.get("inset"),
                       track=kw.get("track", True), approval=kw.get("approval", True))


def el_skirt(c: Ctx, rect, **kw):
    """The 4 m reflector skirt on the spent third stage: she is a 7th-magnitude dot, this is 2-3."""
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    open_ = kw.get("open", c.u)
    r = min(x1 - x0, y1 - y0) * 0.32 * (0.15 + 0.85 * pk.ease_out(open_))
    # the skirt unfolds from the stage
    # the skirt unfolds from the stage: ribs first, then the membrane between them
    for k in range(8):
        a = math.radians(k * 45)
        c.d.line([cx, cy, cx + r * math.cos(a), cy + r * math.sin(a)], fill=tk.amb(0.14 + 0.30 * open_))
    for yy in range(-int(r), int(r) + 1, 3):
        hw = math.sqrt(max(0.0, r * r - yy * yy))
        lam = pk.clamp(1.0 - (yy / max(1.0, r)) ** 2)
        c.d.line([cx - hw, cy + yy, cx + hw, cy + yy], fill=tk.amb(0.05 + 0.28 * lam * open_))
    c.d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=tk.amb(0.35 + 0.4 * open_))
    # her, far ahead and faint
    sx, sy = cx + r * 2.5, cy - r * 0.6
    c.d.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=(255, 255, 255))
    c.text((sx + 6, sy - 6), f"mag {F.SAT_MAG:g}", tk.font(tk.F_MONO, 11), tk.amb(0.45))
    c.text((cx - r - 30, cy + r + 10), f"mag {F.SKIRT_MAG}   d={F.SKIRT_DIA_M:g} m",
           tk.font(tk.F_MONO, 12), tk.amb(0.7))
    return cx, cy, r


def el_ladder(c: Ctx, rect, items, **kw):
    """Milestones as a rising ladder, one step per item, each lighting at its own time. With
    `icons`, every step also carries the block silhouette of the machine it is about."""
    x0, y0, x1, y1 = rect
    n = len(items)
    step_h = (y1 - y0) / (n + 1)
    # the ladder finishes well before the shot does: a half-lit staircase reads as an empty frame
    prog = kw.get("progress", min(1.0, c.u * 1.8 + 0.12)) * n
    f_y = tk.font(tk.F_MONO_B, 13)
    fh = tk.font(tk.F_CJK, 13)
    cell = int(kw.get("cell", 2))
    # the gutter has to clear the widest silhouette in the list, or 天宫 (40 columns wide) runs over
    # the year of the step it belongs to
    widest = max((max(len(r) for r in ic.ALL[(it[3] if len(it) > 3 else kw.get("icons_map", {}).get(it[1], ""))]
                      ) for it in items
                  if (it[3] if len(it) > 3 else kw.get("icons_map", {}).get(it[1]))), default=16)
    gut = (widest * cell + 16) if kw.get("icons") else 0
    for i, item in enumerate(items):
        year, name, note = item[0], item[1], item[2]
        key = item[3] if len(item) > 3 else kw.get("icons_map", {}).get(name)
        yy = y1 - step_h * (i + 1)
        on = pk.clamp(prog - i)
        if on <= 0.01:
            continue
        xx = x0 + 16 + gut + (x1 - x0 - 40 - gut) * (i / max(1, n))
        c.d.line([xx - 10, yy, x1 - 16, yy], fill=tk.amb(0.10 + 0.35 * on))
        c.d.line([xx - 10, yy, xx - 10, yy + step_h], fill=tk.amb(0.10 + 0.3 * on))
        if key:
            ic.draw(c, (0, 0), key, cell=cell, tint="amber", alpha=min(1.0, on),
                    x0=int(xx - gut + 4), x1=int(xx - 12), y0=int(yy - step_h * 0.5),
                    y1=int(yy + step_h * 0.5))
        c.text((xx - 4, yy - 6), str(year), f_y, tk.amb(0.4 + 0.6 * on))
        c.text((xx + 54, yy - 8), str(name), _face(name, 13, 15), tk.amb(0.35 + 0.6 * on))
        c.text((xx + 160, yy - 6), str(note), _face(note, 11, 12), tk.amb(0.25 + 0.45 * on))


def el_bloom(c: Ctx, rect, **kw):
    """A star burst: rays from a point, length driven by the music."""
    cx, cy = kw.get("center", ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2))
    k = kw.get("k", ck.pulse(c.t))
    n = kw.get("n", 24)
    L = min(rect[2] - rect[0], rect[3] - rect[1]) * 0.44
    for i in range(n):
        a = i / n * 2 * math.pi + c.t * 0.15
        r0 = L * 0.16
        r1 = L * (0.35 + 0.65 * k * (0.6 + 0.4 * math.sin(i * 2.3 + c.t * 2)))
        c.d.line([cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                  cx + r1 * math.cos(a), cy + r1 * math.sin(a)], fill=tk.amb(0.25 + 0.5 * k))
    c.d.ellipse([cx - L * 0.10, cy - L * 0.10, cx + L * 0.10, cy + L * 0.10], fill=tk.red(0.85))
    c.d.ellipse([cx - L * 0.16, cy - L * 0.16, cx + L * 0.16, cy + L * 0.16], outline=tk.red(0.4))
    return cx, cy


def el_noise(c: Ctx, rect, **kw):
    """Static: the crowded part of the band."""
    x0, y0, x1, y1 = rect
    rng = random.Random(int(c.t * 12))
    n = kw.get("n", 260)
    for _ in range(n):
        xx = rng.randrange(int(x0), int(x1))
        yy = rng.randrange(int(y0), int(y1))
        v = rng.random()
        if v > 0.75:
            continue
        c.d.point((xx, yy), fill=tk.amb(v * 0.7))


def el_bigtext(c: Ctx, rect, text, **kw):
    """Oversized CJK text. banner_block() only carries Latin (Anton), so CJK goes through the
    system face and gets the same block treatment by hand."""
    x0, y0, x1, y1 = rect
    size = kw.get("size", 64)
    f = tk.font(tk.F_CJK, size)
    col = kw.get("color") or tk.amb(1.0)
    tw = c.d.textlength(text, font=f)
    alpha = kw.get("alpha", 1.0)
    x = kw.get("x", (x0 + x1 - tw) / 2)
    y = kw.get("y", (y0 + y1 - size) / 2)
    if alpha >= 0.999:
        c.text((x, y), text, f, col)
        if kw.get("glow", True):
            gl = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
            ImageDraw.Draw(gl).text((x, y), text, font=f, fill=tuple(col) + (255,))
            gl = gl.filter(ImageFilter.GaussianBlur(6))
            gl.putalpha(gl.getchannel("A").point(lambda v: int(v * 0.5)))
            c.img.paste(Image.alpha_composite(c.img.convert("RGBA"), gl).convert("RGB"), (0, 0))
    else:
        lay = Image.new("RGBA", (int(tw) + 8, int(size * 1.6)), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((4, 4), text, font=f, fill=tuple(col) + (255,))
        c.img.paste(tk.scale_alpha(lay, alpha), (int(x), int(y)), tk.scale_alpha(lay, alpha))
    return x, y, tw


# ---------------------------------------------------------------- things drawn as blocks
# "You can draw with colour blocks -- so draw the spacecraft, the people, the events." These three
# elements are that: a roster where every entry carries the shape of its machine, a log where every
# line carries the shape of its event, and the news wire that fills the broadcast.

def el_craftlist(c: Ctx, rect, items, **kw):
    """A roster of missions, one row each: block icon, year, name, what it was. Rows light in turn."""
    x0, y0, x1, y1 = rect
    n = max(1, len(items))
    pad = kw.get("pad", 16)
    step = (y1 - y0 - pad) / n
    cell = int(kw.get("cell", 3))
    lit = kw.get("lit", 1.0)
    # `pace` decides how much of the shot the reveal owns. At the default 1.7 the last row lights at
    # u = 0.5, so half of a thirteen-second shot plays to a finished list with nothing left to
    # happen -- which is half of why the 07 passage read as static. A shot that has nothing else to
    # show sets pace ~0.95 and spends its whole length filling in.
    prog = kw.get("progress", min(1.0, c.u * kw.get("pace", 1.7) + 0.15)) * n
    f_y = tk.font(tk.F_MONO_B, 14)
    fh = tk.font(tk.F_CJK, 15)
    fm = tk.font(tk.F_MONO, 12)
    # one shared text column, wide enough for the widest machine in the list, so the rows line up
    widest = max((max(len(r) for r in ic.ALL[k]) for _, _, _, k in items), default=16)
    icon_w = widest * cell + 12
    for i, (year, name, note, key) in enumerate(items):
        on = pk.clamp(prog - i)
        if on <= 0.02:
            continue
        on = min(1.0, on)
        yy = y0 + pad + i * step
        col = tk.amb((0.30 + 0.65 * on) * lit)
        ic.draw(c, (0, 0), key, cell=cell, tint="amber", alpha=on,
                x0=x0 + 14, x1=x0 + 14 + icon_w, y0=int(yy), y1=int(yy + step - 4))
        bx = x0 + 24 + icon_w
        c.text((bx, yy + 2), str(year), f_y, tk.amb((0.35 + 0.6 * on) * lit))
        c.text((bx + 62, yy + 1), str(name), fh, col)
        c.text((bx + 210, yy + 4), str(note), fm, tk.amb((0.25 + 0.45 * on) * lit))
        c.d.line([x0 + 14, yy + step - 5, x1 - 14, yy + step - 5], fill=tk.amb(0.09 * lit))
    c.text((x0 + 14, y1 - 14), kw.get("foot", ""), tk.font(tk.F_CJK, 11), tk.amb(0.35 * lit))


def el_afterline(c: Ctx, rect, items, **kw):
    """One ruled span, 1970 to 2026, carrying the nine missions -- and, at the very head of it, the
    twenty-eight days she actually worked.

    The instrument exists for the ratio, not for the roster. Nine missions across fifty-six years is
    a line you can read; the working life of the first of them is *under one pixel* of that line, so
    it cannot be a mark and gets a magnified bracket instead. Nothing else in the film puts the 28
    days and the 56 years on one axis, and that comparison is what section 07 is actually about.
    """
    x0, y0, x1, y1 = rect
    W_, H_ = x1 - x0, y1 - y0
    on = float(kw.get("on", 1.0))
    c.box(rect, kw.get("title", "after  ·  1970 —  2026"),
          (0.34 + 0.22 * ck.pulse(c.t)) * (0.45 + 0.55 * on))
    fm = tk.font(tk.F_MONO, 12)
    fs = tk.font(tk.F_MONO, 11)
    fb = tk.font(tk.F_MONO_B, 30)
    fh = tk.font(tk.F_CJK, 11)

    lx0, lx1 = x0 + int(W_ * 0.08), x1 - int(W_ * 0.03)
    YR0, YR1 = 1970.0, 2026.0
    X = lambda yr: lx0 + (lx1 - lx0) * (yr - YR0) / (YR1 - YR0)
    prog = c.u
    ly = y0 + int(H_ * 0.455)

    # Her working life: 1970-04-24 to 1970-05-14. Twenty days out of 56 years is 0.055 of a year,
    # which on this ruler is 0.9 of a pixel -- hence the bracket rather than a mark.
    d0, d1 = YR0 + 114 / 365.0, YR0 + 134 / 365.0
    xd = (X(d0) + X(d1)) / 2.0

    # --- the span, drawn on
    c.d.line([lx0, ly, lx0 + (lx1 - lx0) * prog, ly], fill=tk.amb(0.85 * on))

    # --- the decade ruler, its own line below
    gy = y0 + int(H_ * 0.74)
    c.d.line([lx0, gy, lx1, gy], fill=tk.amb(0.16))
    for k in range(6):
        xx = X(1970 + 10 * k)
        c.d.line([xx, gy - 5, xx, gy + 5], fill=tk.amb(0.4))
        lab = str(1970 + 10 * k)
        c.text((xx - c.d.textlength(lab, font=fm) / 2, gy + 7), lab, fm, tk.amb(0.45))
    c.text((lx1 - c.d.textlength("2026", font=fm) / 2, gy + 7), "2026", fm, tk.amb(0.7))

    # --- the nine, each standing on its own year
    for i, (year, name, note, key) in enumerate(items):
        yr = float(year)
        xx = X(yr)
        lit = pk.clamp((prog - (yr - YR0) / (YR1 - YR0)) * 14.0)
        if lit <= 0.02:
            continue
        c.d.line([xx, ly, xx, ly + 30], fill=tk.amb(0.12 + 0.55 * lit * on))
        ic.draw(c, (0, 0), key, cell=2, tint="amber", alpha=min(1.0, lit) * on,
                x0=int(xx - 34), x1=int(xx + 34), y0=int(ly + 30), y1=int(ly + 62))
        lab = str(year)
        c.text((xx - c.d.textlength(lab, font=fm) / 2, ly + 68), lab, fm,
               tk.amb((0.30 + 0.6 * lit) * on))
        c.text((xx - c.d.textlength(name, font=fh) / 2, ly + 84), name, fh,
               tk.amb((0.22 + 0.5 * lit) * on))

    # --- 2009: the year the orbit was measured again
    xx = X(2009.0)
    if prog > (2009 - 1970) / 56.0:
        c.d.ellipse([xx - 5, ly - 5, xx + 5, ly + 5], outline=tk.amb(0.9 * on), width=2)
        c.text((xx - c.d.textlength("2009 re-track", font=fs) / 2, ly - 30), "2009 re-track", fs,
               tk.amb(0.6 * on))

    # --- the head of the span, magnified
    cy = y0 + int(H_ * 0.20)
    cx0, cx1 = lx0 + 46, lx0 + 216
    c.d.line([xd, ly - 8, cx0, cy + 8], fill=tk.amb(0.45 * on))
    c.d.line([xd, ly - 8, cx1, cy + 8], fill=tk.amb(0.45 * on))
    c.d.line([cx0, cy, cx1, cy], fill=tk.amb(0.9 * on), width=2)
    for bx in (cx0, cx1):
        c.d.line([bx, cy - 10, bx, cy + 10], fill=tk.amb(0.9 * on), width=2)
    c.text((cx0 + 6, cy - 50), "28", fb, tk.hot(1.0 * on))
    c.text((cx0 + 6 + c.d.textlength("28", font=fb) + 8, cy - 32), "d", tk.font(tk.F_MONO, 17),
           tk.amb(0.8 * on))
    c.text((cx0 + 6, cy + 16), "her working life", fs, tk.amb(0.62 * on))
    c.text((cx0 + 6, cy + 32), "design 20 d  ·  1970-04-24 → 05-14", fs, tk.amb(0.45 * on))
    # the sliver itself: twenty days, drawn three pixels wide because that is the only way to see it
    c.d.line([xd, ly - 12, xd, ly + 12], fill=tk.red(0.95), width=3)

    note = kw.get("note", "nine missions on the span  ·  her 28 d at the head of it")
    if note:
        c.text((lx0, y1 - 30), note, fm, tk.amb(0.42 * on))


def el_fleet(c: Ctx, rect, items, **kw):
    """The nine machines *placed* rather than listed: each drifts on its own band.

    Same data as craftlist, different question. craftlist answers "who" -- a roster you read down.
    This answers "where", which a roster cannot: the same nine names in the frame instead of in a
    column, so the passage stops being one more telling of one list. It is also the right shot to
    cut from into her own planet.
    """
    x0, y0, x1, y1 = rect
    on = float(kw.get("on", 1.0))
    c.box(rect, kw.get("title", "after"), (0.34 + 0.22 * ck.pulse(c.t)) * (0.45 + 0.55 * on))
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0 + 6
    rx, ry = (x1 - x0) * 0.40, (y1 - y0) * 0.33
    fm = tk.font(tk.F_MONO, 13)
    for k in range(3):                                   # the bands they are placed on
        erx, ery = rx * (0.42 + 0.29 * k), ry * (0.42 + 0.29 * k)
        c.d.ellipse([cx - erx, cy - ery, cx + erx, cy + ery],
                    outline=tk.amb((0.11 - 0.02 * k) * on))
    n = max(1, len(items))
    cell = int(kw.get("cell", 2))
    for i, (year, name, note, key) in enumerate(items):
        a = i / n * 2 * math.pi + 1.05 + c.t * 0.03
        px, py = cx + rx * math.cos(a), cy + ry * math.sin(a)
        appear = pk.clamp((c.u * 1.15 - 0.05) * n - i)
        if appear <= 0.02:
            continue
        ic.draw(c, (0, 0), key, cell=cell, tint="amber", alpha=min(1.0, appear) * on,
                x0=int(px - 46), x1=int(px + 46), y0=int(py - 26), y1=int(py + 20))
        lab = str(year)
        c.text((px - c.d.textlength(lab, font=fm) / 2, py + 20), lab, fm,
               tk.amb((0.32 + 0.6 * appear) * on))
    c.text((x0 + 16, y1 - 26), kw.get("foot", "1971 → 2022"), fm, tk.amb(0.35 * on))


def _dwell(c: Ctx, n: int, kw: dict) -> float:
    """How many seconds each line of a list owns the screen.

    An N-line passage staged over a shot of duration `dur` gives every line an equal share of it.
    Two elements showing the same N lines then stay in step with each other and with the music,
    without the direction table having to carry numbers that must agree but are written apart."""
    return float(kw.get("dwell") or (c.dur / max(1, n)))


def el_storylines(c: Ctx, rect, lines, **kw):
    """A log where each line carries the picture of its event, and each line owns its own slot.

    `lines` is [(text, icon_key), ...]. The icons here are small on purpose -- they annotate a
    line. el_scene draws the same events large in the neighbouring pane; both read the same clock
    (`_dwell`), so a line and its picture change on the same frame."""
    x0, y0, x1, y1 = rect
    cell = int(kw.get("cell", 2))
    f = tk.font(tk.F_CJK, 14)
    n = len(lines)
    dwell = _dwell(c, n, kw)
    rise = float(kw.get("rise", min(0.7, dwell * 0.45)))
    step = min(kw.get("step", 34), (y1 - y0 - 20) / max(1, n))
    widest = max((max(len(r) for r in ic.ALL[k]) for _, k in lines if k), default=14)
    icon_w = widest * cell + 12
    here = max(0, min(n - 1, int(max(0.0, c.lt) / dwell)))
    for i, (text, key) in enumerate(lines):
        age = min(1.0, max(0.0, (c.lt - (i - 1) * dwell) / rise))
        if age <= 0:
            continue
        yy = y0 + 12 + i * step
        live = i == here
        col = tk.red(0.9) if str(text).startswith("!") else tk.amb((0.85 if live else 0.42) * age)
        if key:
            ic.draw(c, (0, 0), key, cell=cell, tint="amber", alpha=age,
                    x0=x0 + 10, x1=x0 + 10 + icon_w, y0=int(yy - 4), y1=int(yy + step - 6))
        c.text((x0 + 18 + icon_w, yy), tk.decode(str(text), age * 2.0, c.rng, 42.0, 0.1), f, col)
        if live:
            # the pip that ties the active line to the picture standing beside it
            c.d.rectangle((x0 + 3, int(yy - 2), x0 + 6, int(yy + step - 10)), fill=tk.amb(0.75 * age))


def el_wire(c: Ctx, rect, lines, **kw):
    """A news dispatch, as it would have come off the wire: an agency slug, the body decoded in one
    line at a time, and the punched tape running underneath. This is what fills the broadcast."""
    x0, y0, x1, y1 = rect
    lit = kw.get("lit", 1.0)
    c.box(rect, kw.get("title", "新华社电讯稿  XINHUA  ·  RECV 20.009 MHz"),
          (0.45 + 0.3 * ck.pulse(c.t)) * lit)
    fh = tk.font(tk.F_CJK, 20)
    f = tk.font(tk.F_CJK, 15)
    # the slug is "新华社  北京一九七〇年四月二十五日电": a Chinese agency and dateline with the
    # numerals running through it, so it takes both faces
    tk.mixed_text(c.d, (x0 + 16, y0 + 14), kw.get("kicker", ""), tk.red(0.85 * lit), size=12)
    yy = y0 + 42
    speed = kw.get("speed", 3.2)
    shown = max(0.0, c.lt) * speed
    for i, s in enumerate(lines):
        age = min(1.0, max(0.0, shown - i))
        if age <= 0:
            break
        c.d.rectangle([x0 + 14, yy - 2, x0 + 17, yy + 17], fill=tk.amb(0.35 * (0.4 + 0.6 * age) * lit))
        c.text((x0 + 28, yy), tk.decode(s, age, c.rng, 60.0, 0.06), fh, tk.amb((0.45 + 0.5 * age) * lit))
        yy += 30
    # punched tape: five rows, rolled by the clock, so the panel keeps moving while the voice talks
    ty0 = y1 - 30
    c.d.line([x0 + 14, ty0 - 8, x1 - 14, ty0 - 8], fill=tk.amb(0.12 * lit))
    row = random.Random(int(c.t * 20))
    for r in range(2):
        for k in range(int((x1 - x0 - 40) / 6)):
            xx = x0 + 20 + k * 6
            hole = row.random() < 0.34
            c.d.rectangle([xx, ty0 + r * 9, xx + 3, ty0 + r * 9 + 4],
                          fill=tk.amb((0.12 if hole else 0.40) * lit))
    c.text((x1 - 130, y1 - 16), kw.get("slug", "· 传播 ·"), tk.font(tk.F_CJK, 11), tk.amb(0.45 * lit))


def el_bulletin(c: Ctx, rect, lines, **kw):
    """The formal plaque: a 公报, centred, with a rule above and below the title."""
    x0, y0, x1, y1 = rect
    lit = kw.get("lit", 1.0)
    c.box(rect, kw.get("title", ""), 0.55 * lit)
    cx = (x0 + x1) / 2
    f1 = tk.font(tk.F_CJK, kw.get("size", 26))
    f2 = tk.font(tk.F_CJK, 16)
    yy = y0 + 32
    head = kw.get("head")
    if head:
        tw = c.d.textlength(head, font=f1)
        c.text((cx - tw / 2, yy), head, f1, tk.amb(0.92 * lit))
        c.d.line([cx - tw / 2, yy + 34, cx + tw / 2, yy + 34], fill=tk.amb(0.4 * lit))
        yy += 52
    for s in lines:
        tw = c.d.textlength(s, font=f2)
        c.text((cx - tw / 2, yy), s, f2, tk.amb(0.68 * lit))
        yy += 26


def el_scene(c: Ctx, rect, lines, **kw):
    """The other half of el_storylines: the same events, drawn big.

    Five lines of log leave the largest area of the frame empty. When the frame is about one
    subject -- 钱学森 at the 581 meeting, the train at Jiuquan, the vehicle on the stand -- this
    fills that area with the subject of whichever line is active, at a size where it can actually
    be recognised, captioned by that line. The key on a line selects the small icon (icons.py) and,
    through bigscene.key_of, the large scene, so the two panes can never disagree about an event."""
    x0, y0, x1, y1 = rect
    n = len(lines)
    dwell = _dwell(c, n, kw)
    i = max(0, min(n - 1, int(max(0.0, c.lt) / dwell)))
    text, key = lines[i][0], lines[i][1]
    on = min(1.0, max(0.0, (c.lt - i * dwell) / max(1e-6, min(0.45, dwell * 0.35))))
    c.box(rect, kw.get("title", "SCENE"), (0.35 + 0.30 * ck.pulse(c.t)) * max(0.40, on), spinner=c.t)
    bx = (int(x0 + 16), int(y0 + 38), int(x1 - 16), int(y1 - 54))
    if key:
        name = bs.key_of(key)
        cell = bs.fit_cell(name, bx[2] - bx[0], bx[3] - bx[1], cap=int(kw.get("cap", 14)))
        bs.draw(c, name, bx, cell=cell, tint="amber", alpha=max(0.22, on))
    else:
        # line 0 is the command that opened the run: there is no scene yet, so the pane shows the
        # shell that is about to produce one
        f = tk.font(tk.F_MONO, 26)
        tw = c.d.textlength(text, font=f)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        c.text((cx - tw / 2, cy - 18), text, f, tk.amb(0.85 * max(0.35, on)))
        if (c.t * 2.2) % 1.0 < 0.58:
            c.d.rectangle((cx + tw / 2 + 6, cy - 16, cx + tw / 2 + 19, cy + 12), fill=tk.amb(0.75))
    if key:
        fh = tk.font(tk.F_CJK, 14)
        tw = c.d.textlength(str(text), font=fh)
        c.text(((x0 + x1 - tw) / 2, y1 - 42), str(text), fh, tk.amb(0.85 * on))
    c.text((x0 + 10, y0 + 20), f"{i+1:02d} / {n:02d}", tk.font(tk.F_MONO, 11), tk.amb(0.40 + 0.40 * on))


def el_answer(c: Ctx, rect, question, rows, picture=False, **kw):
    """The frame asks the question, and 东方红一号's own record answers it.

    The song asks three rhetorical questions -- 雾霭萦绕的人生 要如何度过, 蜉蝣一般的人生 要如何度过,
    你被定格的人生 要如何解说 -- and answers none of them in words. The film does not answer them
    either, because the film would only be guessing. What answers is her own log: the same facts the
    rest of the picture is built on (facts.py), set out span by span -- what carried her up, what she
    sang and for how long, and what has been true of her since the transmitter went quiet. Nothing
    on this panel is the film's opinion, and nothing on it is a line taken from a bar that has not
    been sung yet.

    `rows` is [(when, what, icon_key), ...] and reads on the same `_dwell` clock as every other list
    in the film. `picture` adds her portrait for whichever row is live; it is on for the second shot
    of each couplet, which is staged full-width, so the answer is the half of the question that gets
    the room and the drawing."""
    x0, y0, x1, y1 = (int(v) for v in rect)
    n = max(1, len(rows))
    dwell = _dwell(c, n, kw)
    here = max(0, min(n - 1, int(max(0.0, c.lt) / dwell)))
    on = min(1.0, max(0.0, c.lt / 0.45))
    c.box(rect, question, (0.34 + 0.30 * ck.pulse(c.t)) * (0.4 + 0.6 * on), spinner=c.t)

    # the rule the title hangs on, so what follows reads as a page rather than as a caption
    c.d.rectangle((x0 + 12, y0 + 12, x1 - 12, y0 + 12), fill=tk.amb(0.22 * on))
    inner = (x0 + 16, y0 + 26, x1 - 16, y1 - 16)

    rec = inner
    if kw.get("picture", picture):
        cut = inner[0] + int((inner[2] - inner[0]) * float(kw.get("record_frac", 0.56)))
        rec = (inner[0], inner[1], cut - 20, inner[3])
        c.d.rectangle((cut, inner[1] + 6, cut, inner[3] - 6), fill=tk.amb(0.16 * on))
        pr = (cut + 18, inner[1], inner[2], inner[3])
        chart = kw.get("chart")
        if chart:
            # A quantitative chart instead of the block pictogram. Measured against this film's own
            # frames: the same record drawn as a filled area carries five times the ink of the
            # pictogram it replaces, and no amount of brightening fixes a pictogram's thinness.
            el_aero(c, pr, kind=chart, on=on, title=kw.get("chart_title", ""),
                    ml=50, mt=36, mr=14, mb=32, note=kw.get("chart_note", ""))
        else:
            name = bs.key_of(rows[here][2])
            rows_h = len(bs.rows(name))
            cell = bs.fit_cell(name, pr[2] - pr[0], pr[3] - pr[1] - 30, cap=int(kw.get("cap", 14)))
            sp_h = rows_h * cell
            top = pr[1] + max(0, int((pr[3] - pr[1] - 30 - sp_h) / 2))
            bs.draw(c, name, (pr[0], top, pr[2], top + sp_h), cell=cell, tint="amber", alpha=on)
            fh = tk.font(tk.F_CJK, 12)
            cap = str(rows[here][1])
            while len(cap) > 4 and c.d.textlength(cap, font=fh) > (pr[2] - pr[0]):
                cap = cap[:-1]
            tw = c.d.textlength(cap, font=fh)
            c.text(((pr[0] + pr[2] - tw) / 2, top + sp_h + 14), cap, fh, tk.amb(0.50 * on))

    fb = tk.font(tk.F_CJK, 17)
    cell = int(kw.get("cell", 3))
    widest = max((max(len(r) for r in ic.ALL[k]) for _, _, k in rows if k), default=15)
    icon_w = widest * cell + 18
    # The `when` column is not all dates. Three of the nine record lines carry a Chinese span name
    # instead (运载 / 入轨 / 每 114 分钟), and set in the mono face those three came out as empty
    # boxes -- a panel whose whole purpose is to be read, with a third of it unreadable. The column
    # is measured and drawn per script run instead.
    wcol = max(tk.mixed_len(c.d, str(w), size=14) for w, _, _ in rows) + 26
    # the rows fill the panel bottom to top: a record with the whole page to itself and everything
    # bunched into the top third of it would be the same empty pane this panel exists to fill
    avail = rec[3] - rec[1]
    step = min(float(kw.get("step", 150)), avail / n)
    base = rec[1] + max(0.0, (avail - step * n) / 2)
    for i, (when, what, key) in enumerate(rows):
        # The rows come in on their own fast clock rather than on `dwell`. `dwell` is what marks the
        # live row against the lyric; tying the fade-in to it too would leave the panel two-thirds
        # empty for the first half of a three-second shot, which is the empty pane this exists to
        # fill.
        age = min(1.0, max(0.0, (c.lt - i * float(kw.get("spawn", 0.24))) / 0.5))
        if age <= 0:
            continue
        yy = base + i * step
        mid = yy + step * 0.38
        live = i == here
        if key:
            ic.draw(c, (0, 0), key, cell=cell, tint="amber", alpha=age,
                    x0=rec[0], x1=rec[0] + icon_w, y0=int(mid - step * 0.30),
                    y1=int(mid + step * 0.30))
        tk.mixed_text(c.d, (rec[0] + icon_w, mid - 26), str(when), tk.amb((0.70 if live else 0.34) * age),
                      size=14)
        c.text((rec[0] + icon_w + wcol, mid - 20),
               tk.decode(str(what), age * 1.6, c.rng, 46.0, 0.06), fb,
               tk.amb((0.94 if live else 0.46) * age))
        ly = int(yy + step - 28)
        c.d.rectangle((rec[0], ly, rec[2], ly), fill=tk.amb((0.26 if live else 0.11) * age))
        if live:
            c.d.rectangle((rec[0] - 9, int(mid - 26), rec[0] - 6, int(mid + 26)),
                          fill=tk.amb(0.80 * age))
    c.text((rec[0], rec[3] - 2), f"{here + 1:02d} / {n:02d}", tk.font(tk.F_MONO, 11),
           tk.amb(0.34 * on))


FONT_MAP = {}
def el_card(c: Ctx, rect, lines, **kw):
    """A centred plaque. The last card in the film is a fact and is treated as one."""
    x0, y0, x1, y1 = rect
    c.box(rect, kw.get("title", ""), 0.6)
    yy = y0 + 40
    for s, size, col, fnt in lines:
        f = tk.font(FONT_MAP.get(fnt, fnt), size)
        tw = c.d.textlength(s, font=f)
        c.text(((x0 + x1 - tw) / 2, yy), s, f, col)
        yy += size * 1.9


# ---------------------------------------------------------------- air & orbit on screen

def _cjk_line(s: str) -> bool:
    """True if a line has to be set in the CJK face.

    Deliberately *not* `tk.needs_cjk`: that one fires on anything above ASCII, and the mono faces
    carry the maths perfectly well -- measured across the glyph set this film uses, Consolas is
    missing exactly one codepoint (U+2234, which the tables avoid). Sending a formula to 微软雅黑
    because it contains a rho would cost the monospaced alignment that makes it read as algebra.
    So: only real CJK and CJK punctuation switch face.
    """
    return any(ord(ch) > 0x2E7F for ch in str(s))


def _deriv_clock(c: Ctx, lines, t0_frac=0.05, end_frac=0.90, gap=0.11):
    """(start lt, characters already there) per line, and the typing rate.

    Copied from the reference film's ALG: one cursor types the derivation line after line while the
    indentation is there from the start. The rate is *solved for* so that the last line always lands
    before end_frac of the shot, whatever the shot happens to be long -- a fixed rate would overrun
    a short shot and look rushed in a long one.
    """
    pres, need = [], 0
    for i, (s, _) in enumerate(lines):
        if not s:
            pres.append(None)
            continue
        pre = 4 if i == 0 else len(s) - len(s.lstrip(" "))
        pres.append(pre)
        need += len(s) - pre
    nline = sum(1 for p in pres if p is not None)
    t0, tend = t0_frac * c.dur, end_frac * c.dur
    rate = max(6.0, need / max(0.35, (tend - t0) - gap * (nline - 1)))
    t, out = t0, []
    for i, (s, _) in enumerate(lines):
        if pres[i] is None:
            out.append(None)
            continue
        out.append((t, pres[i]))
        t += (len(s) - pres[i]) / rate + gap
    return out, rate


def el_formula(c: Ctx, rect, title="", lines=None, **kw):
    """A derivation typed out line by line.

    The typing is the point: the viewer watches it be *derived* instead of reading a caption, which
    is the difference between "we looked this up" and "this is what her own numbers do". The last
    line is the one that lands, so it gets the larger face and the white-hot layer -- and it is the
    only thing on the frame that is any brighter than the palette, which is the whole reason for the
    white-hot layer existing.
    """
    lines = F.DERIV_DECAY if lines is None else lines
    x0, y0, x1, y1 = rect
    on = float(kw.get("on", 1.0))
    c.box(rect, title, (0.34 + 0.22 * ck.pulse(c.t)) * (0.45 + 0.55 * on))
    clock, rate = _deriv_clock(c, lines, **{k: v for k, v in kw.items()
                                           if k in ("t0_frac", "end_frac", "gap")})
    pad = int(kw.get("pad", 26))
    top = y0 + int(kw.get("top", 46))
    avail = (y1 - pad) - top
    step = float(kw.get("step", 0)) or avail / max(1, len(lines))
    last = max(i for i, (s, _) in enumerate(lines) if s)
    hot_i = int(kw.get("hot_line", last))
    y = top
    for i, (s, sz) in enumerate(lines):
        if not s:
            y += step * 0.42
            continue
        st, pre = clock[i]
        if c.lt < st:
            y += step
            continue
        typed = min(len(s), pre + max(0, int((c.lt - st) * rate)))
        shown = s[:typed]
        f = tk.font(tk.F_CJK if _cjk_line(s) else tk.F_MONO, int(sz))
        done = typed >= len(s)
        col = tk.hot(1.0 * on) if (i == hot_i and done) else tk.amb((0.90 if done else 0.72) * on)
        c.text((x0 + pad, y), shown, f, col)
        if not done:                      # the cursor sits on the character being typed
            wpx = c.d.textlength(shown, font=f)
            c.d.rectangle((x0 + pad + wpx + 1, y + 2,
                           x0 + pad + wpx + 1 + max(5, int(sz) // 2), y + int(sz)),
                          fill=tk.amb(0.85 * on))
        y += step
    # the label discipline, on the panel itself: a derivation must say whose numbers it used,
    # because a formula on screen looks like a fact and this one is arithmetic we did.
    note = kw.get("note", "")
    if note:
        c.text((x0 + pad, y1 - 28), note, tk.font(tk.F_MONO, 12), tk.amb(0.42 * on))


AERO_KINDS = ("decay", "q")


def el_aero(c: Ctx, rect, kind="decay", **kw):
    """A quantitative chart, not a pictogram: axes, grid, ticks, a reading, and a filled area.

    The area is the whole trick. Measured against this film's own frames: the same data drawn as
    lines tops out at 1.5% of pixels above the ink threshold -- *less* than the film already has --
    while drawn as a filled area under the curve it is 7.5%. Ink comes from faces, not from strokes,
    which is why "add more log lines" could never have worked and this can.
    """
    x0, y0, x1, y1 = rect
    on = float(kw.get("on", 1.0))
    box_title = kw.get("title", {"decay": "a(t)", "fleet": "n(t)", "q": "q(t)"}[kind])
    c.box(rect, box_title, (0.34 + 0.22 * ck.pulse(c.t)) * (0.45 + 0.55 * on))
    ix0, iy0 = x0 + int(kw.get("ml", 62)), y0 + int(kw.get("mt", 46))
    ix1, iy1 = x1 - int(kw.get("mr", 26)), y1 - int(kw.get("mb", 40))
    pw, ph = ix1 - ix0, iy1 - iy0
    if pw < 60 or ph < 60:
        return
    fm = tk.font(tk.F_MONO, 11)

    # ---- one branch per quantity, and nothing below this block is chart-specific. Each branch
    # leaves behind X, Y, curve, the two tick tables, the reading, the argument domain (`dom`), how
    # far the solid curve runs (`solid_to`), whether the tail is a dashed extrapolation, and the
    # points that were actually measured.
    if kind == "decay":
        LO, HI = 7590.0, 7810.0
        X = lambda yr: ix0 + pw * (yr - 1970) / 56.0
        Y = lambda v: iy0 + ph * (HI - v) / (HI - LO)

        def curve(yr):
            if yr <= 2009:
                return F.SMA_KM + (F.SMA_2009_KM - F.SMA_KM) * (yr - 1970) / 39.0
            # the record stops at 2009; past it the decline steepens as she comes down, so this is a
            # forward extrapolation and is drawn dashed (and labelled) rather than solid.
            return F.SMA_2009_KM + (F.SMA_2009_KM - F.SMA_KM) * 1.25 * (yr - 2009) / 39.0

        yticks = [(7800, "7800"), (7750, "7750"), (7700, "7700"), (7650, "7650"), (7600, "7600")]
        xticks = [(1970, "1970"), (1980, "1980"), (1990, "1990"), (2000, "2000"), (2009, "2009"),
                  (2026, "2026")]
        unit = "a / km"
        read_v, read_lab, read_sub = "0.884", "m / rev", "39 yr  ·  179934 rev"
        dom, solid_to, dashed = (1970.0, 2026.0), 2009.0, True
        marks = [(1970, F.SMA_KM), (2009, F.SMA_2009_KM)]
    elif kind == "fleet":
        # Not a third drawing of the roster -- a different quantity read off it. The roster says who
        # and when; the count says how fast, which is the one thing a list of nine dates cannot show.
        # The curve is a step function, i.e. an area of stacked rectangles, so it lands in the same
        # ink class as the other two charts (faces, not strokes).
        LO, HI = 0.0, 10.0
        X = lambda yr: ix0 + pw * (yr - 1970.0) / 56.0
        Y = lambda v: iy0 + ph * (HI - v) / (HI - LO)
        years = sorted(float(y) for y, _, _ in F.AFTER)

        def curve(yr):
            return float(sum(1 for y in years if y <= yr))

        yticks = [(9, "9"), (6, "6"), (3, "3"), (0, "0")]
        xticks = [(1971, "1971"), (1984, "1984"), (1997, "1997"), (2010, "2010"), (2022, "2022")]
        unit = "n / missions"
        read_v, read_lab, read_sub = "9", "missions", "1971 → 2022"
        dom, solid_to, dashed = (1970.0, 2026.0), 2026.0, False
        marks = [(1971, 1.0), (2022, 9.0)]
    else:
        LO, HI = 0.0, 22.0                       # kPa
        X = lambda s: ix0 + pw * s / 140.0       # seconds from lift-off
        Y = lambda v: iy0 + ph * (HI - v) / (HI - LO)

        def curve(s):
            if s <= 0 or s > 140:
                return 0.0
            k = F.MAXQ_KPA * (s / F.MAXQ_T) ** 1.6
            return k * max(0.0, 1.0 - 0.55 * max(0.0, s - F.MAXQ_T) / (140 - F.MAXQ_T))

        yticks = [(20, "20"), (15, "15"), (10, "10"), (5, "5"), (0, "0")]
        xticks = [(0, "T+0"), (30, "30"), (60, "60"), (90, "90"), (120, "120")]
        unit = "q / kPa"
        read_v, read_lab, read_sub = "18.9", "kPa @ T+66 s", "M 1.13  ·  T0 12 C"
        dom, solid_to, dashed = (0.0, 140.0), 140.0, False
        marks = [(0, 0.0), (F.MAXQ_T, F.MAXQ_KPA)]

    d_lo, d_hi = dom
    span = X(d_hi)

    # --- grid
    for v, _ in yticks:
        yy = Y(v)
        c.d.line([ix0, yy, ix1, yy], fill=tk.amb(0.085))
    for s, _ in xticks:
        xx = X(s)
        c.d.line([xx, iy0, xx, iy1], fill=tk.amb(0.055))

    # --- the area: this is where the ink comes from
    prog = c.u
    for xx in range(int(ix0), int(min(span, ix1)) + 1):
        u = (xx - ix0) / max(1.0, span - ix0)
        if u > prog:
            break
        arg = d_lo + (d_hi - d_lo) * u
        yc = Y(curve(arg))
        if yc >= iy1:
            continue
        h = max(1.0, iy1 - yc)
        for yy in range(int(yc), int(iy1)):
            c.d.point((xx, yy), fill=tk.amb(0.58 * (1.0 - (yy - yc) / h) ** 0.95 * on))

    # --- axes and ticks
    c.d.line([ix0, iy1, ix1, iy1], fill=tk.amb(0.30))
    c.d.line([ix0, iy0, ix0, iy1], fill=tk.amb(0.30))
    for v, lab in yticks:
        c.text((ix0 - 8 - c.d.textlength(lab, font=fm), Y(v) - 7), lab, fm, tk.amb(0.42))
    for s, lab in xticks:
        c.text((X(s) - c.d.textlength(lab, font=fm) / 2, iy1 + 7), lab, fm, tk.amb(0.42))
    c.text((ix0 - 46, iy0 - 20), unit, fm, tk.amb(0.50))

    # --- the curve itself, brighter than its area, and the points that were measured
    n_samp = 200 if kind == "fleet" else 96       # a step wants more samples than a smooth curve
    pts = []
    for k in range(n_samp + 1):
        arg = d_lo + (solid_to - d_lo) * k / float(n_samp)
        if (arg - d_lo) / max(1e-6, d_hi - d_lo) > prog:
            break
        pts.append((X(arg), Y(curve(arg))))
    if len(pts) > 1:
        c.d.line(pts, fill=tk.amb(0.95 * on), width=2)
    if dashed:                                # the 2009 re-track, and the extrapolation past it
        ex = [(X(t), Y(curve(t))) for t in (2009, 2014, 2019, 2026)]
        for k in range(len(ex) - 1):
            for j in range(4):
                a = (ex[k][0] + (ex[k + 1][0] - ex[k][0]) * j / 4.0,
                     ex[k][1] + (ex[k + 1][1] - ex[k][1]) * j / 4.0)
                b = (ex[k][0] + (ex[k + 1][0] - ex[k][0]) * (j + 0.5) / 4.0,
                     ex[k][1] + (ex[k + 1][1] - ex[k][1]) * (j + 0.5) / 4.0)
                c.d.line([a, b], fill=tk.amb(0.42 * on))
    for arg, v in marks:
        cx, cy = X(arg), Y(v)
        if cx > ix1:
            continue
        c.d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=tk.amb(0.9 * on), width=2)

    # --- the reading: the one white-hot element on this frame
    rx = ix0 + int(pw * 0.30)
    c.text((rx, iy0 + 26), read_v, tk.font(tk.F_MONO_B, 40), tk.hot(1.0 * on))
    c.text((rx + c.d.textlength(read_v, font=tk.font(tk.F_MONO_B, 40)) + 12, iy0 + 46),
           read_lab, tk.font(tk.F_MONO, 14), tk.amb(0.72 * on))
    c.text((rx, iy0 + 84), read_sub, tk.font(tk.F_MONO, 12), tk.amb(0.55 * on))
    # The label discipline survives, in the panel's own alphabet: what is a tracked orbit and what
    # is our arithmetic. Written in Latin because a chart that explains itself in Chinese stops
    # reading as an instrument and starts reading as a diagram.
    note = kw.get("note", "")
    if note:
        c.text((ix0, iy1 + 22), note, tk.font(tk.F_MONO, 12), tk.amb(0.42 * on))


# ---------------------------------------------------------------- the front page


def el_paper(c: Ctx, rect, lines, **kw):
    """A frame set as the front page of a newspaper.

    Where the material genuinely *is* a news page -- a date, a headline, and a list of things that
    happened -- the honest layout is the one a paper uses: 报头 at the top left with the issue and
    the date set opposite it, a heavy rule, the headline across the measure, then the events as
    body text with one picture set into the page. Three faces do the work (楷体 报头 / 黑体 标题 /
    宋体 正文), which is what makes it read as a page rather than as another log.

    The body keeps the same `_dwell` clock as the other programme shots, so the page fills in as
    the passage goes and the picture beside it changes with the line."""
    x0, y0, x1, y1 = (int(v) for v in rect)
    pw = x1 - x0
    red, ink, dim = tk.red(0.92), tk.amb(0.90), tk.amb(0.55)

    # 报头, with the issue number and the date set opposite it on the same line
    masthead = kw.get("masthead", "人民日报")
    fm = tk.font(tk.F_KAI, int(kw.get("mast_size", 52)))
    c.text((x0 + 10, y0 + 2), masthead, fm, red)
    fs = tk.font(tk.F_SONG, 12)
    for i, s in enumerate(kw.get("slug", [])):
        tw = c.d.textlength(s, font=fs)
        c.text((x1 - 14 - tw, y0 + 12 + i * 17), s, fs, dim)

    # the rule that closes the 报头: a heavy red line over a hairline, as on the real page
    ry = y0 + int(kw.get("rule", 64))
    c.d.rectangle((x0 + 8, ry, x1 - 8, ry + 2), fill=red)
    c.d.rectangle((x0 + 8, ry + 5, x1 - 8, ry + 5), fill=tk.amb(0.45))

    # 标题 across the measure, then a 副题 under it
    hy = ry + 16
    head = kw.get("headline", "")
    if head:
        hf = tk.font(tk.F_HEI, int(kw.get("head_size", 38)))
        tw = c.d.textlength(head, font=hf)
        c.text(((x0 + x1 - tw) / 2, hy), head, hf, ink)
        hy += int(kw.get("head_size", 38)) + 6
    sub = kw.get("subhead", "")
    if sub:
        sf = tk.font(tk.F_SONG, 15)
        tw = c.d.textlength(sub, font=sf)
        c.text(((x0 + x1 - tw) / 2, hy), sub, sf, dim)
        hy += 22
    by = hy + 12

    # 图片 set into the page on the right, ruled and captioned
    # Body copy may or may not carry a picture per item: the 公报 is plain text and the 581
    # history has a block icon for every line, so both are first-class here.
    items = [(it, None) if isinstance(it, str) else (it[0], it[1] if len(it) > 1 else None)
             for it in lines]
    n = max(1, len(items))
    text_w = int(pw * float(kw.get("text_frac", 0.52)))
    px0, px1, py0, py1 = x0 + text_w + 26, x1 - 12, by, y1 - 22
    if kw.get("photo"):
        c.d.rectangle((px0, py0, px1, py1), outline=tk.amb(0.38))
        c.d.rectangle((px0 + 3, py0 + 3, px1 - 3, py1 - 3), outline=tk.amb(0.16))
        inner = (px0 + 11, py0 + 10, px1 - 11, py1 - 44)
        cell = bs.fit_cell(bs.key_of(kw["photo"]), inner[2] - inner[0], inner[3] - inner[1],
                           cap=int(kw.get("cap", 12)))
        bs.draw(c, bs.key_of(kw["photo"]), inner, cell=cell, tint="amber")
        cap = kw.get("caption", "")
        if cap:
            cf = tk.font(tk.F_SONG, 12)
            tw = c.d.textlength(cap, font=cf)
            c.text(((px0 + px1 - tw) / 2, py1 - 26), cap, cf, dim)

    # 正文: one dated item per slot, in a ruled column with its icon in the margin
    dwell = _dwell(c, n, kw)
    rise = float(kw.get("rise", min(0.7, dwell * 0.45)))
    here = max(0, min(n - 1, int(max(0.0, c.lt) / dwell)))
    cell = int(kw.get("cell", 3))
    widest = max((max(len(r) for r in ic.ALL[k]) for _, k in items if k), default=0)
    icon_w = (widest * cell + 14) if widest else 0
    bf = tk.font(tk.F_SONG, int(kw.get("body_size", 17)))
    step = kw.get("step") or ((py1 - by - 12) / n)
    for i, (text, key) in enumerate(items):
        age = min(1.0, max(0.0, (c.lt - (i - 1) * dwell) / rise))
        if age <= 0:
            continue
        yy = by + 6 + i * step
        if key:
            ic.draw(c, (0, 0), key, cell=cell, tint="amber", alpha=age,
                    x0=x0 + 4, x1=x0 + 4 + icon_w, y0=int(yy - 6), y1=int(yy + step - 16))
        c.text((x0 + 8 + icon_w, yy), tk.decode(str(text), age * 2.0, c.rng, 40.0, 0.08), bf,
               ink if i == here else tk.amb(0.55 * age))
        ly = int(yy + step - 14)
        c.d.rectangle((x0 + 8, ly, x0 + text_w, ly), fill=tk.amb(0.22 * age))
        if i == here:
            c.d.rectangle((x0 + 2, int(yy + 2), x0 + 5, int(yy + step - 20)), fill=red)


# ---------------------------------------------------------------- staging grammar

# ---------------------------------------------------------------- the right-hand column
# The column used to be a ticker of event lines. At 76 px wide its usable width is 62 px, so every
# CJK entry was cut to four characters before it was drawn -- it was a 548 px tall column of
# fragments saying nothing the header had not already said. (The truncation was in the loop:
# `while len(txt) > 4 and textlength > avail: txt = txt[:-1]`.)
#
# It is now the one thing a 76 px column can carry and the rest of the frame cannot: her own
# section, drawn part by part, with the part the current chapter is about brought forward. Read it
# top to bottom and it is the satellite; read it across the film and it is the chapter list.
#
# Brightening is amb(1.0) and never tk.hot, on purpose: the film keeps exactly one white-hot
# element per frame and that place belongs to the charts.

SUBSYSTEMS = [
    #   icon       label           spec           the live reading
    ("p_ant",   "天线 ×4",      "2.0 m whip",  "2.0 m"),
    ("p_shell", "壳体",         "72f · 1.0 m", "72 f"),
    ("p_batt",  "银锌电池",     "27.3 V",      "27.3 V"),
    ("p_tx",    "短波发射机",   "20.009MHz",   "20.009"),
    ("p_osc",   "乐音装置",     "osc 289",     "289"),
    ("p_skirt", "观测裙",       "4.0m mag2-3", "4.0 m"),
]

# Which part the film is looking at, by chapter. The mapping is the chapter's own subject and not a
# rotation: the shell while she is on the bench, the cell that has to carry the carrier probe, the
# transmitter while the ground locks onto the band, the oscillator where she actually sings, the
# airframe again for the programme that built it, the antenna for the broadcast, the skirt -- the
# thing that made her magnitude 2-3 -- for the passage that asks what came of all of it, and the
# body for the fifty-six years after.
PART_CLOCK = [
    (0.000, 1),      # 00 PRE-FLIGHT / 01 ASSEMBLY
    (29.180, 2),     # 02 FIRST LIGHT      -- the power she is running on
    (58.620, 3),     # 03 UPLINK           -- the band the ground is hunting
    (86.510, 4),     # 04 IGNITION         -- 音源振荡器, this is where she sings
    (114.660, 1),    # 05 581 / 651        -- back to the airframe being built
    (170.010, 0),    # 06 BROADCAST        -- 东方红 太阳升, out on the antennae
    (197.150, 5),    # 07 28 DAYS          -- the skirt on the spent third stage
    (263.210, 1),    # 08 STILL IN ORBIT   -- the 72-facet body, still up there
    (291.760, 0),    # 09 DISPATCH / 10 SIGN-OFF -- the antennae, for the last broadcast
]


def part_at(t: float) -> int:
    return [i for s, i in PART_CLOCK if s <= t][-1]


def el_schematic(c: Ctx, rect, **kw):
    """The satellite, sectioned: six parts stacked, one of them lit, plus its reading."""
    x0, y0, x1, y1 = rect
    d = c.d
    cx = (x0 + x1) / 2.0
    live = part_at(c.t)
    c.box(rect, "", 0.3)
    fh = tk.font(tk.F_CJK, 12)
    fm = tk.font(tk.F_MONO, 10)
    fs = tk.font(tk.F_MONO, 9)
    d.text((x0 + 6, y0 + 6), "拆解", font=fh, fill=tk.amb(0.55))
    d.text((x0 + 6, y0 + 22), "SECTION", font=fs, fill=tk.amb(0.32))
    d.line([x0 + 6, y0 + 34, x1 - 6, y0 + 34], fill=tk.amb(0.18))

    ty0, ty1 = y0 + 42, y1 - 70
    rows = len(SUBSYSTEMS)
    step = (ty1 - ty0) / rows
    for i, (key, name, spec, _read) in enumerate(SUBSYSTEMS):
        yy = ty0 + i * step
        a = 1.0 if i == live else 0.32
        ic.draw(c, (0, 0), key, cell=2, tint="amber", alpha=a,
                x0=int(cx - 26), x1=int(cx + 26), y0=int(yy), y1=int(yy + 30))
        tw = d.textlength(name, font=fh)
        c.text((cx - tw / 2, yy + 34), name, fh, tk.amb(a))
        tw = d.textlength(spec, font=fs)
        c.text((cx - tw / 2, yy + 50), spec, fs, tk.amb(0.45 if i == live else 0.26))
        if i == live:
            d.line([x0 + 4, yy + 1, x0 + 4, yy + 54], fill=tk.amb(0.95), width=2)
            d.line([x1 - 4, yy + 1, x1 - 4, yy + 54], fill=tk.amb(0.95), width=2)
        if i + 1 < rows:
            d.line([x0 + 12, yy + step - 5, x1 - 12, yy + step - 5], fill=tk.amb(0.08))

    # the part's own reading, in the panel's alphabet: which of the six, and its number
    by = y1 - 54
    d.line([x0 + 8, by - 10, x1 - 8, by - 10], fill=tk.amb(0.25))
    c.text((x0 + 8, by), "LIVE", fs, tk.amb(0.4))
    idx = f"{live + 1}/{rows}"
    c.text((x1 - 8 - d.textlength(idx, font=fs), by), idx, fs, tk.amb(0.5))
    c.text((x0 + 8, by + 14), SUBSYSTEMS[live][3], tk.font(tk.F_MONO_B, 15), tk.amb(0.95))


ELEMENTS = {
    "her": el_her, "orbit": el_orbit, "spectrum": el_spectrum, "wave": el_wave, "stars": el_stars,
    "grid": el_grid, "table": el_table, "log": el_log, "beam": el_beam, "banner": el_banner,
    "timeline": el_timeline, "gauge": el_gauge, "rocket": el_rocket, "earth": el_earth,
    "skirt": el_skirt, "ladder": el_ladder, "bloom": el_bloom, "noise": el_noise, "card": el_card,
    "bigtext": el_bigtext, "chinamap": el_chinamap, "craftlist": el_craftlist,
    "storylines": el_storylines, "wire": el_wire, "bulletin": el_bulletin, "scene": el_scene,
    "paper": el_paper, "answer": el_answer, "formula": el_formula, "aero": el_aero,
    "afterline": el_afterline, "fleet": el_fleet,
}

MODES = {
    "split": CENTER,     # subject pane on the left, one element in the pane
    "full": FULL,        # one element across the frame, her pane folded away
    "bleed": (0, 0, W, 720),
    "twin": FULL,        # two elements side by side across the frame
    "float": CENTER,
    "pip": FULL,
    "mirror": CENTER,
    "tiles": CENTER,
    "shell": FULL,
    "raw": FULL,
}


def stage(c: Ctx, mode: str, els: list, kw: dict) -> None:
    """Place the element layers according to the shot's grammar."""
    rect = MODES.get(mode, CENTER)
    if mode == "split":
        el_her(c, LEFT, **kw.get("her", {}))
    if mode == "twin":
        half = (rect[0], rect[1], (rect[0] + rect[2]) / 2 - 10, rect[3])
        half2 = ((rect[0] + rect[2]) / 2 + 10, rect[1], rect[2], rect[3])
        for i, spec in enumerate(els[:2]):
            name, params = spec
            ELEMENTS[name](c, half if i == 0 else half2, **params)
        return
    if mode == "mirror":
        for name, params in els:
            sub = Image.new("RGB", (rect[2] - rect[0], rect[3] - rect[1]), tk.BG)
            cc = Ctx(sub, c.t, c.lt, c.dur, c.rng, c.chapter, c.ui)
            ELEMENTS[name](cc, (0, 0, sub.width, sub.height), **params)
            sub = ImageChops.mirror(sub)
            c.img.paste(sub, (rect[0], rect[1]))
        return
    if mode == "pip":
        for name, params in els:
            ELEMENTS[name](c, rect, **params)
        pr = (rect[2] - 250, rect[1] + 14, rect[2] - 14, rect[1] + 194)
        c.d.rectangle(pr, outline=tk.amb(0.5), fill=tk.BG)
        draw_sat(c, ((pr[0] + pr[2]) / 2, (pr[1] + pr[3]) / 2), 120, spin_phase(c.t), "amber")
        return
    _draw_all(c, rect, els)


def _draw_all(c: Ctx, rect, els) -> None:
    """An element spec is (name, params) or (name, params, rect_override): a shot may partition its
    own pane, which is how a single shot shows a table above a log without a second grammar."""
    for spec in els:
        name, params = spec[0], spec[1]
        r = spec[2] if len(spec) > 2 else rect
        ELEMENTS[name](c, r, **params)
