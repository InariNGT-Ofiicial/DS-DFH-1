"""Big scenes: the picture that belongs in the empty half of the frame.

The small icons in icons.py annotate a line of text. These are the other thing the direction needs:
when a frame is about one subject -- 钱学森 at the 581 meeting, the train arriving at Jiuquan, the
vehicle on the test stand -- the frame should *show* that subject, at a size where you can see it,
in the blank space, rather than leaving the pane empty around five lines of log.

Everything is built from parts (a head, shoulders, a suit; a body, a nozzle, a gantry; a dish on a
pedestal) so the scenes stay consistent with each other and with the film's block texture. Nobody is
caricatured: these are pictograms at the resolution a terminal gives you, drawn to be recognised,
not portraits in the forensic sense.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

import tuikit as tk

# the same glyph ramp the small icons use
LEVELS = {"#": 1.00, "+": 0.62, "-": 0.34, ".": 0.15, " ": 0.0, ",": 0.22}

W, H = 44, 30


class Sheet:
    """A tiny drawing surface that ends up as ASCII rows, so the same renderer draws all of them."""

    def __init__(self, w: int = W, h: int = H, bg: str = " "):
        self.w, self.h = w, h
        self.g = [[bg] * w for _ in range(h)]

    def px(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch
        return self

    def rect(self, x, y, w, h, ch="#", fill=True):
        for j in range(int(y), int(y + h)):
            for i in range(int(x), int(x + w)):
                if fill or j in (int(y), int(y + h) - 1) or i in (int(x), int(x + w) - 1):
                    self.px(i, j, ch)
        return self

    def disc(self, cx, cy, rx, ry, ch="#", fill=True, ring=0.72):
        for j in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for i in range(int(cx - rx) - 1, int(cx + rx) + 2):
                d = ((i - cx) / max(rx, 0.5)) ** 2 + ((j - cy) / max(ry, 0.5)) ** 2
                if d <= 1.0 and (fill or d > ring):
                    self.px(i, j, ch)
        return self

    def line(self, x0, y0, x1, y1, ch="#"):
        n = int(max(abs(x1 - x0), abs(y1 - y0)))
        for k in range(n + 1):
            u = k / n if n else 0.0
            self.px(round(x0 + (x1 - x0) * u), round(y0 + (y1 - y0) * u), ch)
        return self

    def tri(self, a, b, c, ch="#"):
        """Scanline-filled triangle."""
        ys = range(int(min(a[1], b[1], c[1])), int(max(a[1], b[1], c[1])) + 1)
        for y in ys:
            xs = []
            for p, q in ((a, b), (b, c), (c, a)):
                if (p[1] <= y < q[1]) or (q[1] <= y < p[1]):
                    t = (y - p[1]) / (q[1] - p[1])
                    xs.append(p[0] + (q[0] - p[0]) * t)
            if len(xs) >= 2:
                for x in range(int(min(xs)), int(max(xs)) + 1):
                    self.px(x, y, ch)
        return self

    def stamp(self, rows, x, y):
        for j, line in enumerate(rows):
            for i, ch in enumerate(line):
                if ch != " ":
                    self.px(int(x) + i, int(y) + j, ch)
        return self

    def rows(self):
        return ["".join(r) for r in self.g]


# ---------------------------------------------------------------- the parts

def head(s: Sheet, cx, cy, rx, ry, face="#", hair="+", eta=7):
    """A head: face, a hair cap over the top, ears. Readable at roughly 14 cells across."""
    s.disc(cx, cy, rx, ry, face)
    # hair: everything above the brow, allowed to sit a little wider than the skull
    for j in range(int(cy - ry) - 1, int(cy - ry * 0.15)):
        for i in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx = (i - cx) / (rx * 1.06)
            dy = (j - (cy - ry * 0.20)) / (ry * 0.92)
            if dx * dx + dy * dy <= 1.0:
                s.px(i, j, hair)
    # a sweep of hair over one side of the brow, the way the photograph has it
    s.line(cx - rx + 1, cy - ry * 0.25, cx - rx * 0.1, cy - ry * 0.62, hair)
    s.px(cx - rx - 1, cy + 1, face)
    s.px(cx + rx + 1, cy + 1, face)
    del eta
    return s


def glasses(s: Sheet, cx, cy, half=4, ch="."):
    """Two lenses and a bridge. The single strongest cue that a block face is a particular face."""
    s.rect(cx - half - 4, cy, 4, 3, ch, fill=True)
    s.rect(cx + half - 1, cy, 4, 3, ch, fill=True)
    s.px(cx - 1, cy + 1, ch)
    s.px(cx, cy + 1, ch)
    s.px(cx + 1, cy + 1, ch)
    return s


def shoulders(s: Sheet, cx, y, half=13, depth=6, suit="+", shirt="#"):
    """Suit with a collar and a tie, from y down."""
    for j in range(depth):
        w = int(half * (0.62 + 0.38 * (j / max(1, depth - 1))))
        s.rect(cx - w, y + j, 2 * w + 1, 1, suit, fill=True)
    # collar: a V of shirt in the middle
    for j in range(min(depth, 4)):
        w = 1 + j
        s.rect(cx - w, y + j, 2 * w + 1, 1, shirt, fill=True)
    s.rect(cx - 2, y + 4, 5, depth - 4, shirt, fill=True)
    return s


def rocket(s: Sheet, cx, top, bot, half=3, body="+", edge="#", fins=True, noz=True):
    """A stack: nose cone, body, fins, nozzle."""
    s.tri((cx - half, top + half), (cx + half, top + half), (cx, top - 2), edge)
    s.rect(cx - half, top + half, 2 * half + 1, bot - top - half, body, fill=True)
    s.rect(cx - half, top + half, 2 * half + 1, bot - top - half, edge, fill=False)
    if fins:
        s.tri((cx - half, bot - 4), (cx - half - 3, bot + 1), (cx - half, bot + 1), edge)
        s.tri((cx + half, bot - 4), (cx + half + 3, bot + 1), (cx + half, bot + 1), edge)
    if noz:
        s.tri((cx - half, bot + 1), (cx + half, bot + 1), (cx, bot + 3), edge)
    return s


def dish(s: Sheet, cx, cy, r, face="#", back="+", stem=True):
    """A parabolic antenna, opening up-left, on a pedestal."""
    s.disc(cx, cy, r, r * 0.62, face, fill=True)
    s.disc(cx, cy, r, r * 0.62, back, fill=False, ring=0.55)
    if stem:
        s.line(cx, cy + r * 0.62, cx, cy + r * 1.5, back)
        s.rect(cx - 2, cy + r * 1.5, 5, 2, back, fill=True)
    return s


def figure(s: Sheet, cx, top, h=10, head_r=2, ch="#", arm=None):
    """A standing person: head, trunk, two legs, optionally one arm raised."""
    s.disc(cx, top + head_r, head_r, head_r + 1, ch)
    s.rect(cx - 2, top + 2 * head_r + 2, 5, int(h * 0.5), ch, fill=True)
    s.rect(cx - 2, top + int(h * 0.75), 2, int(h * 0.35), ch, fill=True)
    s.rect(cx + 1, top + int(h * 0.75), 2, int(h * 0.35), ch, fill=True)
    if arm:
        s.line(cx + 2, top + int(h * 0.45), cx + arm[0], top + arm[1], ch)
        s.line(cx - 2, top + int(h * 0.45), cx - 5, top + int(h * 0.62), ch)
    return s


def flag(s: Sheet, x, y, w=8, h=5, pole=9, ch="#", pole_ch="+"):
    s.rect(x, y - pole, 1, pole, pole_ch, fill=True)
    s.tri((x + 1, y - pole + 1), (x + 1 + w, y - pole + int(h / 2)), (x + 1, y - pole + h), ch)
    return s


# ---------------------------------------------------------------- the scenes
# Keyed exactly like the story lines in direction.py, so a line can name its picture.

def _rally(s: Sheet):
    """1958-05: the slogan raised on a banner, and the thing it promised overhead."""
    # the banner, hung between two poles, with four blocks where the words sit
    s.rect(4, 7, 36, 10, "+", fill=True)
    s.rect(4, 7, 36, 10, "#", fill=False)
    for k in range(4):
        s.rect(8 + k * 8, 12, 6, 3, "#", fill=True)
    s.rect(5, 5, 1, 22, "+", fill=True)
    s.rect(38, 5, 1, 22, "+", fill=True)
    # the satellite everybody is promising themselves
    s.disc(22, 3, 4, 3, "+")
    s.disc(22, 3, 4, 3, "#", fill=False, ring=0.8)
    s.line(18, 4, 15, 6, "+")
    s.line(26, 4, 29, 6, "+")
    for k in range(5):
        figure(s, 6 + k * 8, 19, h=8, head_r=2, ch="+" if k % 2 else "#")
    s.line(0, 28, 44, 28, ".")
    return s


def _qian(s: Sheet):
    """1958-08 / 1968-02: the portrait. Short hair, high forehead, glasses, suit and tie."""
    head(s, 22, 12, 9, 11, face="#", hair="+")
    glasses(s, 22, 11, half=2)
    # nose and mouth, kept to the centre line so the face does not smear
    s.line(22, 13, 22, 17, ".")
    s.px(21, 17, ".")
    s.rect(19, 19, 7, 1, ".")
    shoulders(s, 22, 24, half=15, depth=6, suit="+", shirt="#")
    s.tri((20, 27), (25, 27), (22, 30), ".")
    return s


def _hold(s: Sheet):
    """1959-01: the programme, stood down. A satellite behind a stop bar, and an arrow down."""
    s.disc(20, 10, 6, 6, "+")
    s.disc(20, 10, 6, 6, "#", fill=False, ring=0.82)
    s.line(14, 10, 14, 14, "+")
    s.line(26, 10, 26, 14, "+")
    # the stop bar, drawn over her
    s.rect(9, 4, 4, 20, "#", fill=True)
    s.rect(27, 4, 4, 20, "#", fill=True)
    s.line(20, 18, 20, 26, "#")
    s.tri((17, 25), (23, 25), (20, 29), "#")
    return s


def _t7m(s: Sheet):
    """1960-02: the sounding rocket, and the 8 km it reached."""
    rocket(s, 16, 12, 27, half=3, body="+", edge="#")
    s.line(20, 9, 40, 9, ".")
    s.line(40, 9, 40, 27, ".")
    for x in range(21, 40, 3):
        s.px(x, 9, "-")
    s.rect(36, 7, 5, 4, "#", fill=True)
    s.line(6, 27, 42, 27, ".")
    s.disc(38, 9, 1, 1, "#")
    return s


def _twodesk(s: Sheet):
    """1965-01: two proposals landing on the same desk."""
    s.rect(6, 21, 32, 3, "+", fill=True)
    s.rect(9, 24, 3, 6, "+", fill=True)
    s.rect(32, 24, 3, 6, "+", fill=True)
    for x in (11, 24):
        s.rect(x, 12, 9, 9, "#", fill=True)
        for j in range(2, 8, 2):
            s.rect(x + 1, 12 + j, 7, 1, ".", fill=True)
    s.line(20, 5, 20, 12, "-")
    s.line(20, 5, 20, 3, "#")
    return s


def _meeting(s: Sheet):
    """1965-10: the 42 days. A long table with the people who argued at it."""
    for i, x in enumerate((4, 11, 18, 25, 32, 39)):
        figure(s, x, 2, h=7, head_r=2, ch="+")
    s.rect(2, 17, 40, 3, "#", fill=True)
    s.rect(2, 20, 40, 1, "+", fill=True)
    s.rect(3, 21, 2, 8, "+", fill=True)
    s.rect(39, 21, 2, 8, "+", fill=True)
    s.rect(12, 11, 8, 6, "#", fill=True)
    s.rect(24, 12, 7, 5, "+", fill=True)
    return s


def _institute(s: Sheet):
    """1966-01: 651 设计院. A building with a sign over the door."""
    s.rect(8, 9, 28, 18, "+", fill=True)
    s.rect(8, 9, 28, 18, "#", fill=False)
    for r in range(3):
        for k in range(6):
            s.rect(11 + k * 4, 12 + r * 5, 3, 3, "#", fill=(r == 1 and k % 3 == 0))
    s.rect(19, 22, 6, 5, "#", fill=True)
    s.rect(10, 4, 24, 4, "#", fill=True)
    s.rect(10, 4, 24, 4, ".", fill=False)
    flag(s, 6, 9, w=7, h=5, pole=12, ch="#", pole_ch="+")
    s.line(0, 27, 44, 27, ".")
    return s


def _station(s: Sheet):
    """1966-05: 701 工程处. The ground station, listening."""
    dish(s, 27, 8, 9, face="+", back="#")
    s.rect(6, 19, 14, 8, "+", fill=True)
    s.rect(6, 19, 14, 8, "#", fill=False)
    s.rect(9, 22, 8, 2, "#", fill=True)
    s.rect(11, 25, 4, 2, "#", fill=True)
    for k in range(3):
        s.line(27 + 2 * k, 17, 27 + 4 * k, 21, "#")
    s.line(0, 27, 44, 27, ".")
    return s


def _podium(s: Sheet):
    """1968-02: 钱学森 at the rostrum."""
    head(s, 22, 7, 5, 6, face="#", hair="+")
    glasses(s, 22, 7, half=1)
    s.rect(19, 12, 7, 1, ".")
    shoulders(s, 22, 14, half=9, depth=4, suit="+", shirt="#")
    s.rect(12, 18, 21, 11, "+", fill=True)
    s.rect(12, 18, 21, 11, "#", fill=False)
    s.line(30, 15, 30, 20, "#")
    s.px(30, 14, "#")
    return s


def _team18(s: Sheet):
    """1968: the eighteen who went."""
    for r in range(3):
        for k in range(6):
            figure(s, 4 + k * 7, 2 + r * 9, h=8, head_r=2,
                   ch="#" if r == 0 else ("+" if r == 1 else "-"))
    s.line(0, 29, 44, 29, ".")
    return s


def _testfire(s: Sheet):
    """1969-09: the third stage, firing clean on the stand."""
    s.rect(4, 2, 3, 26, "+", fill=True)
    s.rect(37, 2, 3, 26, "+", fill=True)
    for y in (6, 14, 22):
        s.rect(4, y, 36, 1, "+", fill=True)
    rocket(s, 22, 6, 20, half=3, body="+", edge="#", fins=True)
    for k in range(8):
        w = max(1, 5 - k)
        s.rect(22 - w, 21 + k, 2 * w + 1, 1, "#" if k < 4 else "-", fill=True)
    for k in range(5):
        s.line(10 - k, 27, 34 + k, 27, "-")
    return s


def _chamber(s: Sheet):
    """1969-09: the flight article in the thermal-vacuum chamber."""
    s.rect(10, 4, 24, 24, "+", fill=False)
    s.rect(10, 4, 24, 24, "#", fill=False)
    s.disc(22, 15, 6, 6, "#")
    s.disc(22, 15, 6, 6, "+", fill=False, ring=0.75)
    s.line(22, 21, 22, 25, "#")
    s.line(16, 12, 13, 9, "#")
    s.line(28, 12, 31, 9, "#")
    s.line(16, 18, 13, 21, "#")
    s.line(28, 18, 31, 21, "#")
    for k in range(3):
        s.rect(35, 6 + k * 4, 6, 3, "#", fill=(k == 0))
    return s


def _train(s: Sheet):
    """1970-04-01: the special train, and the vehicle it was carrying."""
    s.rect(2, 18, 12, 7, "+", fill=True)
    s.rect(2, 12, 8, 6, "+", fill=True)
    s.rect(2, 12, 8, 6, "#", fill=False)
    s.rect(4, 9, 4, 3, "#", fill=True)
    for k in range(3):
        s.disc(4 + k * 4, 26, 2, 2, "#")
    s.rect(15, 18, 27, 3, "+", fill=True)
    rocket(s, 28, 8, 18, half=3, body="+", edge="#", fins=False, noz=False)
    for k in range(4):
        s.disc(19 + k * 6, 26, 2, 2, "#")
    s.line(0, 28, 44, 28, ".")
    s.line(5, 4, 39, 4, "-")
    return s


def _mate(s: Sheet):
    """1970-04-09: the satellite coming down onto the top of the vehicle.

    The sphere with four antennae is the whole point of the frame -- it is the only shape in this
    film that says 东方红一号 and nothing else -- so it gets the middle of the sheet, hanging from
    a hoist, with the third stage waiting underneath it."""
    # gantry beam, and the cable the satellite is coming down on
    s.rect(2, 2, 40, 1, "+", fill=True)
    s.rect(21, 3, 2, 5, "+", fill=True)
    # 东方红一号: sphere, four antennae, opening out on the diagonals
    s.disc(22, 12, 5, 5, "#")
    s.disc(22, 12, 5, 5, "+", fill=False, ring=0.72)
    for dx, dy in ((-3, 3), (3, 3), (-3, -3), (3, -3)):
        s.line(22 + dx, 12 + dy, 22 + dx * 2, 12 + dy * 2, "+")
    # the vehicle's top stage waiting underneath, nozzle down
    s.rect(19, 20, 7, 6, "+", fill=True)
    s.rect(19, 20, 7, 6, "#", fill=False)
    s.tri((19, 26), (25, 26), (22, 29), "#")
    s.tri((19, 20), (15, 24), (19, 24), "#")
    s.tri((25, 20), (29, 24), (25, 24), "#")
    s.line(2, 29, 42, 29, ".")
    return s


def _phone(s: Sheet):
    """1970-04-23: the call from the Premier."""
    s.rect(8, 12, 28, 6, "+", fill=True)
    s.rect(8, 12, 28, 6, "#", fill=False)
    s.rect(4, 9, 8, 12, "#", fill=True)
    s.rect(32, 9, 8, 12, "#", fill=True)
    s.rect(10, 14, 24, 2, ".", fill=True)
    for k in range(7):
        s.px(10 + k * 4, 20, "+")
        s.px(11 + k * 4, 22, "+")
        s.px(12 + k * 4, 20, "+")
    s.line(20, 8, 20, 3, "+")
    s.disc(20, 2, 1, 1, "#")
    return s


def _approve(s: Sheet):
    """1970-04-24 15:30: the approval, and the seal on it."""
    s.rect(8, 2, 28, 26, "#", fill=True)
    s.rect(8, 2, 28, 26, ".", fill=False)
    for r in range(9):
        s.rect(11, 6 + r * 2, 22 - (r % 3) * 4, 1, ".", fill=True)
    s.disc(29, 20, 5, 5, "#")
    s.disc(29, 20, 5, 5, ".", fill=False, ring=0.6)
    s.disc(29, 20, 2, 2, ".")
    return s


def _liftoff(s: Sheet):
    """1970-04-24 21:35."""
    rocket(s, 22, 4, 20, half=3, body="+", edge="#")
    for k in range(9):
        w = max(1, 6 - k // 2)
        s.rect(22 - w, 21 + k, 2 * w + 1, 1, "#" if k < 5 else "-", fill=True)
    for k in range(7):
        s.line(22 - 12 + k, 29, 22 - 4 + k, 22, "-")
        s.line(22 + 12 - k, 29, 22 + 4 - k, 22, "-")
    s.line(0, 29, 44, 29, ".")
    return s


# ---------------------------------------------------------------- her own record
# The song asks three rhetorical questions and never answers any of them. The film does not answer
# them either -- the film would only be guessing. What answers is 东方红一号's own record, drawn the
# way the rest of the film is drawn: her sphere, her four antennae, her launch, her track. Each
# question owns two shots; the second of the pair is staged full-width and adds her portrait for
# whichever line of the record is live.

def _ascent(s: Sheet):
    """1970-04-24: the stack climbing, with the layers of the atmosphere under it."""
    for y, w in ((24, 7), (17, 8), (10, 9)):
        s.line(0, y, 44, y, ".")
        s.rect(44 - w, y - 2, w - 1, 2, ",", fill=True)
    rocket(s, 17, 3, 21, half=3, body="+", edge="#", fins=False)
    for k in range(8):
        w = max(1, 5 - k)
        s.rect(17 - w, 22 + k, 2 * w + 1, 1, "#" if k < 4 else "-", fill=True)
    s.line(0, 29, 44, 29, ".")
    return s


def _orbit1(s: Sheet):
    """入轨: her, the four antennae out, the limb of the Earth under her and the track above.

    The limb is the rim of the disc and nothing else. Filled, it reads as a dark puddle in the
    corner of the sheet rather than as a planet; a single bright edge reads as the horizon."""
    s.disc(4, 32, 24, 13, "-", fill=False, ring=0.97)
    for k in range(45):                                 # the ground track, a shallow arc
        s.px(k, 9 - int(5 * math.sin(k / 44.0 * math.pi)), ".")
    s.disc(30, 21, 5, 5, "#")
    s.disc(30, 21, 5, 5, "+", fill=False, ring=0.72)
    for dx, dy in ((-3, 3), (3, 3), (-3, -3), (3, -3)):
        s.line(30 + dx, 21 + dy, 30 + dx * 2, 21 + dy * 2, "+")
    return s


def _radio(s: Sheet):
    """播送: her, and three rings of the 20.009 MHz tone on their way down to the ground."""
    s.disc(22, 8, 5, 5, "#")
    s.disc(22, 8, 5, 5, "+", fill=False, ring=0.72)
    for dx, dy in ((-3, 3), (3, 3), (-3, -3), (3, -3)):
        s.line(22 + dx, 8 + dy, 22 + dx * 2, 8 + dy * 2, "+")
    for k, r in enumerate((10, 14, 18)):
        for t in range(41):
            a = math.radians(20 + t * 140 / 40.0)       # an arc opening downward
            s.px(round(22 + r * math.cos(a)), round(8 + r * math.sin(a)),
                 "#" if k == 0 else "+")
    s.rect(2, 27, 40, 1, ".", fill=True)
    dish(s, 22, 27, 4, face="+", back="#", stem=False)
    return s


def _loop(s: Sheet):
    """One turn every 114 minutes: about twelve and a half of them a day, one after another."""
    for k in range(181):
        a = k / 180.0 * 2 * math.pi
        s.px(round(22 + 18 * math.cos(a)), round(16 + 8 * math.sin(a)), "-")
    for k in range(6):
        a = k / 6.0 * 2 * math.pi + 0.5
        s.disc(22 + 18 * math.cos(a), 16 + 8 * math.sin(a), 2, 2, "#" if k == 0 else "+")
    return s


def _silent(s: Sheet):
    """1970-05-14, 电池耗尽: the bus falls, the tone stops, and the trace goes flat."""
    s.line(3, 3, 3, 24, "+")                            # the axis
    pts = [(4, 5), (13, 5), (13, 9), (21, 9), (21, 15), (28, 15), (28, 22)]
    for k in range(len(pts) - 1):
        (xa, ya), (xb, yb) = pts[k], pts[k + 1]
        s.line(xa, ya, xb, ya, "-")
        s.line(xb, ya, xb, yb, "-")
    s.line(4, 22, 42, 22, "#")                          # flat: nothing more
    # She is the dimmest object in any of these scenes -- the trace going flat is the event, and she
    # is what is left after it -- but a filled "," disc reads as a smear rather than as a satellite.
    # A small + body inside a - rim keeps her a silhouette at the lowest level that still has one.
    s.disc(36, 14, 3, 3, "+")
    s.disc(36, 14, 3, 3, "-", fill=False, ring=0.72)
    for dx, dy in ((-2, 2), (2, 2), (-2, -2), (2, -2)):
        s.line(36 + dx, 14 + dy, 36 + dx * 2, 14 + dy * 2, ",")
    return s


def _retrack(s: Sheet):
    """2009, the thirty-ninth year: the ground finds her again and measures the track."""
    dish(s, 9, 15, 7, face="+", back="#", stem=True)
    s.rect(3, 24, 12, 5, "+", fill=True)
    s.line(13, 11, 33, 3, "#")                          # out
    s.line(15, 14, 35, 6, "-")                          # and back
    s.disc(36, 4, 3, 3, "#")
    s.disc(36, 4, 3, 3, "+", fill=False, ring=0.72)
    s.line(0, 29, 44, 29, ".")
    return s


def _still56(s: Sheet):
    """2026, the fifty-sixth year: still on the same track, a long way round from where she began."""
    for k in range(181):
        a = k / 180.0 * 2 * math.pi
        s.px(round(23 + 19 * math.cos(a)), round(17 + 9 * math.sin(a)), "-")
    s.disc(4, 17, 2, 2, ",")                            # 1970
    s.disc(42, 17, 3, 3, "#")                           # 2026
    s.disc(42, 17, 3, 3, "+", fill=False, ring=0.72)
    for dx, dy in ((-2, 2), (2, 2), (-2, -2), (2, -2)):
        s.line(42 + dx, 17 + dy, 42 + dx * 2, 17 + dy * 2, "+")
    s.line(0, 29, 44, 29, ".")
    return s


BUILDERS = {
    "rally": _rally, "qian": _qian, "hold": _hold, "t7m": _t7m, "twodesk": _twodesk,
    "meeting42": _meeting, "institute": _institute, "station": _station, "podium": _podium,
    "team18": _team18, "testfire": _testfire, "chamber": _chamber, "train": _train,
    "mate": _mate, "phone": _phone, "approve": _approve, "liftoff": _liftoff,
    "ascent": _ascent, "orbit1": _orbit1, "radio": _radio, "loop": _loop,
    "silent": _silent, "retrack": _retrack, "still56": _still56,
}


# A story line names its small icon (icons.py); the same line wants the matching big scene.
# Keeping the map here rather than in the direction table means a line can be re-keyed to a
# different small icon without anyone having to remember to re-key the picture as well.
BIG = {
    "slogan": "rally",       # 1958-05  we should build satellites too
    "speaker": "qian",       # 1958-08  代号 581  组长 钱学森
    "pause": "hold",         # 1959-01  stood down
    "grounded": "hold",
    "t7m": "t7m",            # 1960-02  T-7M  8 km
    "desk": "twodesk",       # 1965-01  two proposals, one desk
    "meeting": "meeting42",  # 1965-10  友谊宾馆  42 天
    "building": "institute", # 1966-01  651 设计院
    "dish": "station",       # 1966-05  701 工程处
    "rostrum": "podium",     # 1968-02  院长 钱学森
    "team": "team18",        # 1968-xx  航天十八勇士
    "teststand": "testfire", # 1969-09  三级试车
    "sphere": "chamber",     # 1969-09  正样星环境模拟
    "train": "train",        # 1970-04-01  专列抵达酒泉
    "dock": "mate",          # 1970-04-09  星箭对接
    "phone": "phone",        # 1970-04-23  总理来电
    "approve": "approve",    # 1970-04-24  15:30  主席批准
    "liftoff": "liftoff",    # 1970-04-24  21:35  点火
}


def key_of(key: str) -> str:
    """Resolve a story-line key to a scene name. A key that is already a scene name passes through."""
    if key in BUILDERS:
        return key
    return BIG.get(key, "station")


@lru_cache(None)
def rows(name: str) -> tuple[str, ...]:
    return tuple(BUILDERS[name](Sheet()).rows())


@lru_cache(64)
def sprite(name: str, cell: int = 12, tint: str = "amber") -> Image.Image:
    g = rows(name)
    r_, c_ = len(g), max(len(x) for x in g)
    lum = Image.new("L", (c_, r_), 0)
    px = lum.load()
    for j, line in enumerate(g):
        for i, ch in enumerate(line):
            v = LEVELS.get(ch, 0.0)
            if v > 0:
                px[i, j] = int(round(v * 255))
    big = lum.resize((c_ * cell, r_ * cell), Image.NEAREST)
    if cell >= 3:
        gut = Image.new("L", big.size, 255)
        d = ImageDraw.Draw(gut)
        for x in range(cell - 1, big.width, cell):
            d.line([x, 0, x, big.height], fill=0)
        for y in range(cell - 1, big.height, cell):
            d.line([0, y, big.width, y], fill=0)
        big = ImageChops.multiply(big, gut)
    rgb = tk.tint_colorize(big, tint).convert("RGBA")
    rgb.putalpha(big.point(lambda v: 0 if v < 8 else min(255, int(v * 1.3))))
    return rgb


def fit_cell(name: str, max_w: int, max_h: int, cap: int = 16) -> int:
    g = rows(name)
    r_, c_ = len(g), max(len(x) for x in g)
    return max(2, min(cap, int(max_w / c_), int(max_h / r_)))


def draw(c, name: str, box, cell: int | None = None, tint: str = "amber", alpha: float = 1.0,
         cap: int = 16):
    x0, y0, x1, y1 = (int(v) for v in box)
    cell = cell or fit_cell(name, x1 - x0, y1 - y0, cap)
    sp = sprite(name, cell, tint)
    if alpha < 0.999:
        sp = tk.scale_alpha(sp, alpha)
    # A scene must never leave its pane: fit_cell already guarantees this, but a caller passing an
    # explicit cell can still ask for too much, and a stray 30-pixel overhang reads as a bug.
    if sp.width > x1 - x0 or sp.height > y1 - y0:
        sp = sp.crop((0, 0, min(sp.width, x1 - x0), min(sp.height, y1 - y0)))
    c.img.paste(sp, (x0 + (x1 - x0 - sp.width) // 2, y0 + (y1 - y0 - sp.height) // 2), sp)
    return sp.size
