"""Composition, chrome and the per-frame entry point.

Fixed layer order, as in the reference PV:
  1. the scene's own drawing on the stage background
  2. carriers (ink) - none in this build; the two panes share one stage instead
  3. the subject herself (drawn inside her pane element)
  4. chrome: header, the section panel, lyric band - drawn once per frame, never transformed
  5. CRT post

A frame is a pure function of its index: the post has no temporal trail on purpose, so any block of
frames can be rendered on any worker and the result is bit-identical to a single-threaded run.
"""
from __future__ import annotations

import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import direction as dr
import facts as F
import prims as pk
import pvclock as ck
import scenes as sc
import tuikit as tk

W, H = 1280, 720
FPS = ck.FPS

# The palette is the reference PV's own 'amber' phosphor, used as designed: UI amber for the ground
# segment, ERR red for 东方红. F_HEAD points into a tree that is not shipped here, so it is rebound
# to the system mono face - the only unavoidable substitution in this build.
tk.F_HEAD = os.environ.get("PV_F_HEAD", "C:/Windows/Fonts/consolab.ttf")
tk.F_CJK = os.environ.get("PV_F_CJK", "C:/Windows/Fonts/msyh.ttc")
tk.F_MONO = os.environ.get("PV_F_MONO", "C:/Windows/Fonts/consola.ttf")
tk.F_MONO_B = os.environ.get("PV_F_MONO_B", "C:/Windows/Fonts/consolab.ttf")
tk.F_BANNER = os.environ.get("PV_F_BANNER", "C:/Windows/Fonts/arialbd.ttf")
sc.FONT_MAP.update(CJK=tk.F_CJK, MONO=tk.F_MONO, MONO_B=tk.F_MONO_B, HEAD=tk.F_HEAD)

pk.BG_AT = lambda t: BASE[0]


def base(t: float) -> Image.Image:
    """The stage: near-black with a faint dot field, so bare frames still read as a terminal."""
    img = Image.new("RGB", (W, H), tk.BG)
    img.paste(tk.dot_field(W, H, 24), (0, 0))
    return img


BASE = [base(0.0)]


# ---------------------------------------------------------------- chrome

def header(c: sc.Ctx) -> None:
    d = c.d
    f = tk.font(tk.F_MONO, 13)
    fh = tk.font(tk.F_HEAD, 13)
    col = tk.red(0.95) if c.alert == "err" else tk.amb(0.9)
    d.text((24, 14), "DFH-1 / MISSION 651   jiuquan", font=fh, fill=col)
    t = c.t
    mm, ss = int(t // 60), t % 60
    alt = F.PERIGEE_KM + (F.APOGEE_KM - F.PERIGEE_KM) * (0.5 - 0.5 * math.cos(t / (F.PERIOD_MIN * 60) * 2 * math.pi))
    line = f"T+ {mm:02d}:{ss:04.1f}   alt {alt:6.0f} km   v {7.9 - 1.4 * math.sin(t * 0.11):5.2f} km/s   bus 27.3 V"
    d.text((392, 15), line, font=f, fill=tk.amb(0.5))
    # signal strength ribbon, drawn on the beat grid
    x0, y0, w = 1000, 24, 160
    pts = []
    for px in range(w):
        tau = t - (w - px) / w * 1.6
        v = 0.5 + 0.5 * math.sin(tau * 2.1) * math.cos(tau * 0.7)
        v *= (0.35 + 0.65 * (1.0 if t < F.LIFE_ACTUAL_D * 86400 else 0.3))
        pts.append((x0 + px, y0 + 12 - v * 10))
    d.line(pts, fill=tk.amb(0.45))
    d.rectangle([x0, y0 - 4, x0 + w, y0 + 28], outline=tk.amb(0.2))
    c.text((24, 34), ck.section_at(t), tk.font(tk.F_HEAD, 11), tk.amb(0.45))


def schematic(c: sc.Ctx) -> None:
    """The right-hand column: her own section, part by part (see scenes.SUBSYSTEMS).

    What used to be here was a ticker of event lines. In a 76 px column it had 62 px to draw in, so
    every CJK entry was silently cut to four characters and the column spent the whole film showing
    fragments of sentences the header had already said in full. The section panel replaces it with
    something only this column can do: a part-by-part reading of the satellite the film is about,
    with the part the current chapter belongs to lit."""
    sc.el_schematic(c, sc.TICK)


def lyric_state(t: float):
    """Typewriter rules: a line appears on its first syllable, holds until the next line, and when an
    instrumental gap is coming it rests one beat and fades over the next."""
    rows = ck.ROWS
    for i, (a, b, s) in enumerate(rows):
        if a - 1e-6 <= t < b:
            age = t - a
            fade = 1.0
            gap = (rows[i + 1][0] - b) if i + 1 < len(rows) else 99.0
            if gap > 2.0:
                tail = b - 2 * ck.BEAT
                if t > tail:
                    fade = pk.clamp((b - t) / (2 * ck.BEAT))
            return s, age, fade
        if t < a:
            break
    return None, 0.0, 0.0


def lyric_band(c: sc.Ctx) -> None:
    band = (24, 616, 1256, 680)
    # The broadcast is not a rest. Where the song hands the words to a newsreader, the band carries
    # the dispatch instead of five empty beats.
    sp = ck.spoken_line(c.t)
    if sp:
        s, age, dur = sp
        c.box(band, "新华社电讯  ·  播报", (0.5 + 0.3 * ck.pulse(c.t)))
        f = tk.font(tk.F_CJK, 22)
        txt = tk.decode(s, min(age, 6.0), c.rng, 26.0, 0.08)
        tw = c.d.textlength(txt, font=f)
        c.text(((band[0] + band[2] - tw) / 2, band[1] + 12), txt, f, tk.red(0.95))
        # a receive lamp, ticking over while the reader talks
        for k in range(3):
            on = ((c.t * 2.6) % 3) < (k + 1)
            c.d.rectangle([band[2] - 28 + k * 7, band[1] + 12, band[2] - 24 + k * 7, band[1] + 16],
                          fill=tk.red(0.9 if on else 0.2))
        return
    s, age, fade = lyric_state(c.t)
    if not s or fade <= 0.01:
        return
    c.box(band, "stdout · 歌词", (0.45 + 0.3 * ck.pulse(c.t)) * fade)
    if "♪" in s:
        # the eighth-note glyph is missing from the CJK face; the same mark in a common bullet
        txt = s.replace("♪", "·")
    else:
        rate = max(6.0, len(s) / 0.25)
        txt = tk.decode(s, min(age, 4.0), c.rng, rate, 0.10)
    f = tk.font(tk.F_CJK, 22)
    tw = c.d.textlength(txt, font=f)
    c.text(((band[0] + band[2] - tw) / 2, band[1] + 12), txt, f, tk.amb(0.95 * fade))


def chrome(img: Image.Image, c: sc.Ctx) -> Image.Image:
    out = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.img, c._d = ov, ImageDraw.Draw(ov)
    header(c)
    schematic(c)
    out.alpha_composite(ov)
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.img, c._d = band, ImageDraw.Draw(band)
    lyric_band(c)
    out.alpha_composite(band)
    c.img, c._d = img, ImageDraw.Draw(img)
    return out


# ---------------------------------------------------------------- one shot


def render_shot(shot: dict, t: float) -> Image.Image:
    img = base(t)
    rng = random.Random((int(t * FPS) * 7919) ^ (dr.index_of(shot["name"]) * 104729))
    c = sc.Ctx(img, t, t - shot["start"], shot["end"] - shot["start"], rng,
               chapter=ck.section_at(t), ui=ck.ui_gain(t), params=shot)
    sc.stage(c, shot["mode"], shot["els"], dict(her=shot.get("her", {})))
    return chrome(img, c)


# ---------------------------------------------------------------- transitions

def _delay_fn(spec: dict, cut: float, dur: float):
    kind = spec.get("kind", "reflow")
    region = sc.CENTER
    if kind == "inward":
        return pk.inward(spec.get("seed", (W // 2, H // 2)), cut - dur, cut), region
    if kind == "pan":
        d = spec.get("dir", "right")
        vec = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}[d]
        o = {"right": (0, H // 2), "left": (W, H // 2), "down": (W // 2, 0), "up": (W // 2, H)}[d]
        return pk.sweep(o, vec, cut - dur, (W + H) / dur), (0, 0, W, H)
    seed = (spec.get("seed") or (sc.CENTER[0] + 380, sc.CENTER[1] + 280))
    return pk.radial(seed, cut - dur, 2600.0), (0, 0, W, H)


def frame(t: float) -> Image.Image:
    shot = dr.shot_at(t)
    i = dr.index_of(shot["name"])
    img = render_shot(shot, t)
    if i > 0:
        prev = dr.SHOTS[i - 1]
        spec = dr.transition(prev, shot)
        if spec is not None:
            dur = spec.get("frames", 12) / FPS
            cut = shot["start"]
            if t >= cut - dur:
                old = render_shot(prev, t)
                delay, region = _delay_fn(spec, cut, dur)
                img = pk.reveal(old, img, t, delay, region=region, cell=(8, 16), dur=0.09,
                                seed=i, density=0.35)
                if spec.get("kind") == "crt":
                    k = pk.clamp((t - (cut - dur)) / dur)
                    bar = int(H * (1 - k))
                    d = ImageDraw.Draw(img)
                    d.line([0, bar, W, bar], fill=tk.amb(0.9), width=2)
                    if k > 0.55:
                        img = ImageChops.add(img.convert("RGB"),
                                             Image.new("RGB", img.size, (26, 20, 10)))
    return post(img, ck.glow_arc(t))


def post(img: Image.Image, bloom: float) -> Image.Image:
    """Bloom, scanlines and vignette. No temporal trail: the frame must stay reproducible."""
    glow = img.filter(ImageFilter.GaussianBlur(4))
    out = ImageChops.add(img, glow.point(lambda v: int(v * bloom)))
    out = out.convert("RGBA")
    out.alpha_composite(tk.scanlines())
    out.alpha_composite(tk.vignette(False))
    return out.convert("RGB")
