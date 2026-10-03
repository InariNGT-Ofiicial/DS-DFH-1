"""tuikit: terminal-look drawing primitives for the amber-phosphor TUI PV.

PIL only (no numpy). Everything draws onto a 1280x720 RGB canvas.

Colours are semantic and come from a palette picked by the TUI_PALETTE environment variable:
  UI   (kept under the old name AMBER) - the system, i.e. "your" terminal
  ME   (BLUE_*)                        - reserved for a second voice; unused in this film, which has
                                         exactly one subject (the spacecraft, drawn in UI amber)
  ERR  (RED)                           - errors
  ANOM                                 - anomalies / warnings

Inherited from the reference PV (`MisakaZentai/world-execute-me-dsh-pv`, MIT). Two things that were
specific to that film have been taken out here and are documented in docs/PORTING.md: the external
character artwork (this film draws every pixel procedurally) and the bundled display face.
"""

from __future__ import annotations

import math
import os
import random
import re
import zlib
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1280, 720

DS_BLUE = (77, 107, 254)  # DeepSeek brand blue, #4D6BFE
PALETTES = {
    # v2 look: amber phosphor system, anomalies in phosphor green
    "amber": dict(BG=(8, 6, 4), UI=(255, 176, 0), ERR=(255, 58, 40), ANOM=(70, 255, 140),
                  ME_LO=(4, 8, 34), ME_MID=DS_BLUE, ME_HI=(196, 212, 255), ME_TEXT=(126, 152, 255)),
    # deep-sea night: cold white-steel system on navy black, log-level yellow for anomalies
    "deepsea": dict(BG=(4, 7, 15), UI=(200, 214, 234), ERR=(255, 59, 48), ANOM=(255, 204, 0),
                    ME_LO=(4, 8, 34), ME_MID=DS_BLUE, ME_HI=(196, 212, 255), ME_TEXT=(120, 148, 255)),
    # green phosphor system, yellow anomalies
    "phosphor": dict(BG=(3, 8, 5), UI=(92, 255, 140), ERR=(255, 58, 40), ANOM=(255, 214, 0),
                     ME_LO=(4, 8, 34), ME_MID=DS_BLUE, ME_HI=(196, 212, 255), ME_TEXT=(126, 152, 255)),
}
PALETTE = os.environ.get("TUI_PALETTE", "amber")
_P = PALETTES[PALETTE]

BG = _P["BG"]
AMBER = UI = _P["UI"]
RED = ERR = _P["ERR"]
ANOM = _P["ANOM"]
BLUE_LO = _P["ME_LO"]
BLUE_MID = _P["ME_MID"]
BLUE_HI = _P["ME_HI"]
BLUE_TEXT = _P["ME_TEXT"]

# Every face is resolved through the environment so the kit carries no assumption about a machine.
# The defaults are the Windows faces this build was made with; docs/FONTS.md lists equivalents for
# other systems. Nothing here is shipped with the repository - see NOTICE.md.
F_MONO = os.environ.get("PV_F_MONO", "C:/Windows/Fonts/consola.ttf")
F_MONO_B = os.environ.get("PV_F_MONO_B", "C:/Windows/Fonts/consolab.ttf")
# The reference PV set its headings in Space Mono Bold, which is not redistributable and therefore not
# shipped. The system mono face is the closest stand-in and the only substitution in this build.
F_HEAD = os.environ.get("PV_F_HEAD", "C:/Windows/Fonts/consolab.ttf")
F_BANNER = os.environ.get("PV_F_BANNER", "C:/Windows/Fonts/arialbd.ttf")
F_CJK = os.environ.get("PV_F_CJK", "C:/Windows/Fonts/msyh.ttc")
F_SYM = os.environ.get("PV_F_SYM", "C:/Windows/Fonts/seguisym.ttf")  # math glyphs Consolas lacks: ∃ ⟨ ⟩ ⊢ ∀
# The newspaper front page needs the three faces a Chinese paper is actually set in: a brush face
# for the masthead, a hei for the headline, and a song for the body.
F_KAI = os.environ.get("PV_F_KAI", "C:/Windows/Fonts/STKAITI.TTF")     # 华文楷体  报头
F_HEI = os.environ.get("PV_F_HEI", "C:/Windows/Fonts/simhei.ttf")      # 黑体      标题
F_SONG = os.environ.get("PV_F_SONG", "C:/Windows/Fonts/simsun.ttc")    # 宋体      正文

SCR = "!<>-_\\/[]{}=+*^?#%$&@01|~:;"


def mix(c, level, base=BG):
    level = max(0.0, min(1.0, level))
    return tuple(int(base[i] + (c[i] - base[i]) * level) for i in range(3))


UI_GAIN = [1.0]  # set per frame by the engine; < 1 drains the system colour ("you have left")
BOXES = [True]   # False in the bare-shell layout: panels lose their frames


def amb(level):
    return mix(AMBER, level * UI_GAIN[0])


def red(level):
    return mix(RED, level)


def blue(level):
    return mix(BLUE_TEXT, level)


def anom(level):
    return mix(ANOM, level)


# ---------------------------------------------------------------- the white-hot layer
# The palette tops out at UI amber (255,176,0) -- luminance 143.7 -- and post only ever subtracts, so
# on its own the film structurally has no highlight. That was the single largest measured gap to the
# reference film: 0.00% of pixels above luminance 190 against its 0.51%, peak 155.8 against 242.0.
#
# This is the same amber ramp pushed to near-white at the top end. It is rationed on purpose: at most
# one element per frame may use it, so the frame keeps a single brightest thing to look at.
HOT_GAIN = [1.0]


def hot(level):
    c = amb(level)
    w = max(0.0, min(1.0, (level - 0.5) / 0.5)) * HOT_GAIN[0]
    return tuple(int(c[i] + (247 - c[i]) * w) for i in range(3))


def ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def smooth(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


@lru_cache(None)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def needs_cjk(ch: str) -> bool:
    """True for every codepoint the mono faces in this build cannot draw.

    Consolas and Space Mono carry Latin, the box-drawing set and the common punctuation, and
    nothing else: every CJK ideograph, the CJK punctuation and the fullwidth forms come back as an
    empty box. The test is deliberately the crude one -- anything above ASCII goes to the CJK face,
    which has the Latin and the punctuation too -- because the failure it guards against (a line of
    tofu) is much worse than the cost of it (an em dash set in 微软雅黑).
    """
    return ord(ch) > 0x7F


def script_runs(s: str) -> list[tuple[str, bool]]:
    """Split a string into maximal runs of (text, needs_cjk), so each run can get its own face."""
    out: list[list] = []
    for ch in str(s):
        wide = needs_cjk(ch)
        if out and out[-1][1] == wide:
            out[-1][0] += ch
        else:
            out.append([ch, wide])
    return [(t, w) for t, w in out]


def mixed_len(d: ImageDraw.ImageDraw, s: str, mono: str | None = None, size: int = 13,
              cjk: str | None = None) -> float:
    """Width `mixed_text` will draw, so a caller can lay a column out before drawing it."""
    mono, cjk = mono or F_MONO, cjk or F_CJK
    return sum(d.textlength(run, font=font(cjk if wide else mono, size))
               for run, wide in script_runs(s))


def mixed_text(d: ImageDraw.ImageDraw, xy, s, fill, mono: str | None = None, size: int = 13,
               cjk: str | None = None, anchor: str = "la") -> float:
    """Draw one line that mixes Chinese and ASCII, each run in the face that can actually draw it.

    scenes._face() picks a single face for the whole string. That is right for a cell that is all one
    script and wrong for a line like "长征一号  /  CZ-1  29.46 m": set whole in the CJK face the
    figures lose the terminal's mono rhythm, and set whole in the mono face the Chinese comes out as
    four empty boxes -- which is what the rocket's own data line was doing. Splitting by script costs
    one textlength per run and fixes both.

    Both faces share one baseline, taken from the mono face, so a mixed line reads as one line. The
    anchor follows PIL: 'la' means (x, y) is the top of the ascender, as d.text() defaults to.
    """
    mono, cjk = mono or F_MONO, cjk or F_CJK
    x = float(xy[0])
    if anchor == "la":
        y, a = float(xy[1]) + font(mono, size).getmetrics()[0], "ls"
    else:
        y, a = float(xy[1]), anchor
    if not any(needs_cjk(ch) for ch in str(s)):
        d.text((x, y), str(s), font=font(mono, size), fill=fill, anchor=a)
        return d.textlength(str(s), font=font(mono, size))
    for run, wide in script_runs(s):
        f = font(cjk if wide else mono, size)
        d.text((x, y), run, font=f, fill=fill, anchor=a)
        x += d.textlength(run, font=f)
    return x - xy[0]


# ---------------------------------------------------------------- text effects

def decode(s: str, age: float, rng: random.Random, rate: float = 45.0, settle: float = 0.12,
           corrupt: float = 0.0) -> str:
    """Typewriter where each new character flickers through random glyphs for `settle` seconds."""
    if age is None:
        n = len(s)
        age = 1e9
    else:
        n = min(len(s), max(0, int(age * rate)))
    out = []
    for i in range(n):
        ch = s[i]
        a = age - i / rate
        if ch != " " and (a < settle or (corrupt > 0 and rng.random() < corrupt)):
            ch = rng.choice(SCR)
        out.append(ch)
    return "".join(out)


def tokenize(s: str) -> list[str]:
    """Toy BPE-looking split: words and punctuation; long words break into two pieces."""
    toks = []
    for w in re.findall(r"[A-Za-z']+|[^\sA-Za-z']", s):
        if len(w) > 7:
            k = len(w) // 2 + 1
            toks += [w[:k], w[k:]]
        else:
            toks.append(w)
    return toks


def token_id(tok: str) -> int:
    return zlib.crc32(tok.lower().encode()) % 100000


# ---------------------------------------------------------------- masks


@lru_cache(None)
def grid_mask(w: int, h: int, px: int) -> Image.Image:
    m = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(m)
    if px >= 3:
        for x in range(px - 1, w, px):
            d.line([x, 0, x, h], fill=0)
    for y in range(2 * px - 1, h, 2 * px):
        d.line([0, y, w, y], fill=70)
    return m


TINTS = {"blue": (BLUE_LO, BLUE_HI, BLUE_MID), "amber": (BG, AMBER, None), "red": (BG, RED, None),
         "anom": (BG, ANOM, None)}


def tint_colorize(lum: Image.Image, tint: str) -> Image.Image:
    lo, hi, mid = TINTS[tint]
    if mid is None:
        return ImageOps.colorize(lum, black=lo, white=hi)
    return ImageOps.colorize(lum, black=lo, white=hi, mid=mid)


def scale_alpha(sp: Image.Image, k: float) -> Image.Image:
    if k >= 0.999:
        return sp
    out = sp.copy()
    out.putalpha(sp.getchannel("A").point(lambda a: int(a * max(0.0, k))))
    return out


def paste_clipped(img: Image.Image, sp: Image.Image, x: int, y: int, rect: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = rect
    cx0, cy0 = max(x, x0), max(y, y0)
    cx1, cy1 = min(x + sp.width, x1), min(y + sp.height, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    part = sp.crop((cx0 - x, cy0 - y, cx1 - x, cy1 - y))
    img.paste(part, (cx0, cy0), part)


def glitch_paste(img: Image.Image, sp: Image.Image, x: int, y: int, amount: float, rng: random.Random,
                 rect=None, strip: int = 8) -> None:
    for sy in range(0, sp.height, strip):
        off = int(rng.gauss(0, 22 * amount)) if rng.random() < amount else 0
        part = sp.crop((0, sy, sp.width, min(sp.height, sy + strip)))
        if rect:
            paste_clipped(img, part, x + off, y + sy, rect)
        else:
            img.paste(part, (x + off, y + sy), part)


# ---------------------------------------------------------------- glyph ascii art

GLYPH_RAMP = " .:-=+*#%@"


@lru_cache(None)
def glyph_grid(src: Image.Image, cols: int, rows: int) -> tuple[list[str], Image.Image]:
    """ASCII art of an image: edge cells get a directional stroke, interior cells a density glyph.
    Returns the text rows and a per-cell brightness image (cols x rows)."""
    small = src.resize((cols, rows), Image.LANCZOS)
    lum = small.convert("L")
    alpha = small.getchannel("A")
    gx = lum.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4, offset=128))
    gy = lum.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4, offset=128))
    L, A, X, Y = lum.load(), alpha.load(), gx.load(), gy.load()
    bright = Image.new("L", (cols, rows), 0)
    B = bright.load()
    lines = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if A[c, r] < 110:
                row.append(" ")
                continue
            v = L[c, r] / 255
            ex, ey = (X[c, r] - 128) / 32, (Y[c, r] - 128) / 32
            mag = math.hypot(ex, ey)
            if mag > 1.1:
                ang = (math.degrees(math.atan2(ey, ex)) + 180) % 180
                row.append("|" if ang < 22.5 or ang >= 157.5 else "\\" if ang < 67.5 else "-" if ang < 112.5 else "/")
                B[c, r] = 255
            else:
                row.append(GLYPH_RAMP[min(len(GLYPH_RAMP) - 1, 1 + int(v * (len(GLYPH_RAMP) - 1)))])
                B[c, r] = int(255 * (0.35 + 0.65 * v))
        lines.append("".join(row))
    return lines, bright


def glyph_sprite(src: Image.Image, cols: int, rows: int, size: int = 11, scramble: float = 0.0,
                 rng: random.Random | None = None, tint: str = "blue", reveal: float = 1.0) -> Image.Image:
    """Render the glyph art as an RGBA image. `scramble` swaps that fraction of glyphs for noise;
    `reveal` < 1 hides a random subset of cells (used for resolving and disintegrating)."""
    f = font(F_MONO_B, size)
    cw, ch = f.getlength("M"), round(size * 1.15)
    lines, bright = glyph_grid(src, cols, rows)
    if (scramble > 0 or reveal < 1) and rng is not None:
        out = []
        for r, line in enumerate(lines):
            row = []
            for ch_ in line:
                if ch_ == " ":
                    row.append(" ")
                elif reveal < 1 and rng.random() > reveal:
                    row.append(" ")
                elif scramble > 0 and rng.random() < scramble:
                    row.append(rng.choice(SCR))
                else:
                    row.append(ch_)
            out.append("".join(row))
        lines = out
    size_px = (int(cols * cw) + 2, rows * ch)
    txt = Image.new("L", size_px, 0)
    d = ImageDraw.Draw(txt)
    for r, line in enumerate(lines):
        d.text((0, r * ch), line, font=f, fill=255)
    b = bright.resize(size_px, Image.NEAREST)
    lum = ImageChops.multiply(txt, b)
    rgb = tint_colorize(lum, tint).convert("RGBA")
    rgb.putalpha(txt)
    return rgb


# ---------------------------------------------------------------- big letters

@lru_cache(None)
def banner_bits(text: str, rows: int, cell_aspect: float) -> Image.Image:
    f = font(F_BANNER, 220)
    tmp = Image.new("L", (int(f.getlength(text)) + 60, 300), 0)
    ImageDraw.Draw(tmp).text((30, 10), text, font=f, fill=255)
    tmp = tmp.crop(tmp.getbbox())
    cols = max(1, int(round(tmp.width / tmp.height * rows * cell_aspect)))
    return tmp.resize((cols, rows), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)


@lru_cache(None)
def banner_block(text: str, rows2: int, px: int, fg: tuple, bg: tuple, max_w: int = 1200) -> Image.Image:
    bits = banner_bits(text, rows2, 1.0)
    px = max(2, min(px, max_w // bits.width))
    size = (bits.width * px, bits.height * px)
    big = bits.resize(size, Image.NEAREST)
    alpha = ImageChops.multiply(big, grid_mask(size[0], size[1], px))
    rgb = ImageOps.colorize(big, black=bg, white=fg).convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


# ---------------------------------------------------------------- widgets

def box(d: ImageDraw.ImageDraw, x0, y0, x1, y1, title: str = "", level: float = 0.5, color=AMBER,
        spinner: float | None = None) -> None:
    if not BOXES[0]:
        return
    d.rectangle([x0, y0, x1, y1], outline=mix(color, level))
    L = 7
    for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([px, py, px + sx * L, py], fill=mix(color, min(1.0, level + 0.4)), width=2)
        d.line([px, py, px, py + sy * L], fill=mix(color, min(1.0, level + 0.4)), width=2)
    if title:
        if spinner is not None:
            title = "|/-\\"[int(spinner * 8) % 4] + " " + title
        # The title face has to change with the title. F_HEAD is a mono face and carries no CJK, so
        # a Chinese panel title set in it comes out as a row of empty boxes -- which is exactly what
        # every 中文 title in this film was doing before this line existed.
        cjk = any(needs_cjk(ch) for ch in title)
        f = font(F_CJK if cjk else F_HEAD, 13)
        tw = d.textlength(f" {title} ", font=f)
        d.rectangle([x0 + 12, y0 - 9, x0 + 12 + tw, y0 + 9], fill=BG)
        d.text((x0 + 12, y0 - 10), f" {title} ", font=f, fill=mix(color, min(1.0, level + 0.35)))


def dot_chart(d: ImageDraw.ImageDraw, x, y, w, h, fn, progress: float, color, sx: int = 5, sy: int = 5,
              clip_top: bool = True, axis: bool = True):
    cols, rows = w // sx, h // sy
    if axis:
        for i in range(0, cols, 2):
            d.point((x + i * sx, y + h), fill=amb(0.28))
        for r in range(0, rows, 3):
            d.point((x - 4, y + r * sy), fill=amb(0.28))
    prev, last = None, None
    for i in range(cols):
        u = i / (cols - 1)
        if u > progress:
            break
        v = fn(u)
        if clip_top:
            v = min(1.0, v)
        r = int(round((1 - max(0.0, v)) * (rows - 1)))
        span = range(min(prev, r), max(prev, r) + 1) if prev is not None else [r]
        for rr in span:
            d.rectangle([x + i * sx, y + rr * sy, x + i * sx + 1, y + rr * sy + 1], fill=color)
        prev, last = r, (x + i * sx, y + r * sy)
    return last


def heat_cell(d, x, y, w, h, v, color=AMBER) -> None:
    """One heat-map cell drawn as a shade block, so the matrix still reads as terminal text."""
    v = max(0.0, min(1.0, v))
    d.rectangle([x, y, x + w - 2, y + h - 2], fill=mix(color, 0.06 + 0.94 * v))


@lru_cache(None)
def dot_field(w: int, h: int, step: int = 16) -> Image.Image:
    im = Image.new("RGB", (w, h + step), BG)
    d = ImageDraw.Draw(im)
    for y in range(0, h + step, step):
        for x in range(0, w, step):
            d.point((x, y), fill=mix(UI, 0.1))
    return im


@lru_cache(None)
def conv_maps(src: Image.Image, cols: int, rows: int) -> list[tuple[str, Image.Image]]:
    """Feature maps of an RGBA image, at cell resolution.

    The reference PV ran this over a character sprite. This film has no external artwork, so the
    argument is the image itself - the spacecraft drawn by `scenes.draw_sat` is passed in.
    """
    flat = Image.new("RGBA", src.size, (0, 0, 0, 255))
    flat.alpha_composite(src)
    small = flat.convert("L").resize((cols, rows), Image.LANCZOS)
    kernels = [
        ("sobel_x", [-1, 0, 1, -2, 0, 2, -1, 0, 1]),
        ("sobel_y", [-1, -2, -1, 0, 0, 0, 1, 2, 1]),
        ("laplace", [0, 1, 0, 1, -4, 1, 0, 1, 0]),
        ("sharpen", [0, -1, 0, -1, 5, -1, 0, -1, 0]),
        ("emboss", [-2, -1, 0, -1, 1, 1, 0, 1, 2]),
        ("blur", [1, 2, 1, 2, 4, 2, 1, 2, 1]),
    ]
    out = []
    for name, k in kernels:
        if name == "blur":
            fm = small.filter(ImageFilter.Kernel((3, 3), k, scale=16))
        elif name == "emboss":
            fm = small.filter(ImageFilter.Kernel((3, 3), k, scale=1, offset=128))
        elif name == "sharpen":
            fm = small.filter(ImageFilter.Kernel((3, 3), k, scale=1))
        else:  # signed response -> magnitude
            pos = small.filter(ImageFilter.Kernel((3, 3), k, scale=1))
            neg = small.filter(ImageFilter.Kernel((3, 3), [-v for v in k], scale=1))
            fm = ImageChops.add(pos, neg)
        out.append((name, ImageOps.autocontrast(fm, cutoff=1)))
    return out


def tile_from_lum(lum: Image.Image, px: int, tint: str = "amber", reveal_rows: int | None = None) -> Image.Image:
    if reveal_rows is not None:
        lum = lum.copy()
        ImageDraw.Draw(lum).rectangle([0, reveal_rows, lum.width, lum.height], fill=0)
    size = (lum.width * px, lum.height * px)
    big = lum.resize(size, Image.NEAREST)
    alpha = ImageChops.multiply(big.point(lambda v: 255 if v > 18 else 0), grid_mask(size[0], size[1], px))
    rgb = tint_colorize(big, tint).convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


def noise_tile(cols: int, rows: int, px: int, tint: str = "blue") -> Image.Image:
    n = Image.effect_noise((cols, rows), 90).point(lambda v: max(0, min(255, int((v - 60) * 1.6))))
    return tile_from_lum(n, px, tint)


# ---------------------------------------------------------------- post

@lru_cache(None)
def scanlines() -> Image.Image:
    s = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    for y in range(0, H, 3):
        d.line([0, y, W, y], fill=(0, 0, 0, 55))
    return s


LYRIC_LIFT = [False]  # set by the engine: keep the vignette off the bottom lyric band


@lru_cache(None)
def vignette(lift: bool = False) -> Image.Image:
    small = Image.new("L", (64, 36), 0)
    px = small.load()
    for y in range(36):
        # rows 30-35 are y 600-720, where the lyric band sits
        k = 1.0 if not lift or y < 30 else {30: 0.7, 31: 0.45}.get(y, 0.3)
        for x in range(64):
            dx, dy = (x - 31.5) / 32, (y - 17.5) / 18
            px[x, y] = int(255 * k * min(1.0, max(0.0, (dx * dx + dy * dy) - 0.35) * 0.55))
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    v.putalpha(small.resize((W, H), Image.BILINEAR))
    return v


def post(img: Image.Image, prev: Image.Image | None, trail: float = 0.42, bloom: float = 0.35) -> Image.Image:
    if prev is not None and trail > 0:
        img = ImageChops.lighter(img, prev.point(lambda v: int(v * trail)))
    glow = img.filter(ImageFilter.GaussianBlur(4))
    img = ImageChops.add(img, glow.point(lambda v: int(v * bloom)))
    img = img.convert("RGBA")
    img.alpha_composite(scanlines())
    img.alpha_composite(vignette(LYRIC_LIFT[0]))
    return img.convert("RGB")
