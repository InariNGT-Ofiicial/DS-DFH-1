"""The clock. Calibrated on the real audio, not guessed.

Measured (tools/calib.py, 2026-10-01): the median spacing between vocal lines is 3.3300 s and one
line is four beats, so BPM = 72.072 (beat 0.8325 s). The onset-on-grid score confirms it: 72.07 and
its 1/2 and 2x score within 2% of each other, which is the signature of a correct grid rather than
of an octave error.

Everything downstream snaps to this grid. The hard anchors for the staging are the vocal onsets
themselves (a human wrote those times), never the grid alone.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FPS = 24
W, H = 1280, 720
SONG_LEN = 330.069           # decoded length of the wav (ffprobe says 330.096 with mp3 padding)
END_T = 330.0

BPM = 72.072
BEAT = 60.0 / BPM            # 0.83252 s
FIRST_LINE = 1.360           # the first sung line is beat 0 of the vocal grid
BAR = BEAT * 4               # one lyric line = one bar


def beat_t(n: float) -> float:
    return FIRST_LINE + n * BEAT


def beat_index(t: float) -> int:
    return math.floor((t - FIRST_LINE) / BEAT + 1e-6)


def snap(t: float, div: int = 1) -> float:
    """Quantise t to the 1/div of a beat grid."""
    step = BEAT / div
    return FIRST_LINE + round((t - FIRST_LINE) / step) * step


def pulse(t: float, decay: float = 0.30) -> float:
    """0..1, 1 exactly on the beat. A piano decays slower than a hi-hat, hence the 0.30."""
    return math.exp(-max(0.0, t - beat_t(beat_index(t))) / decay)


def keyframes(t: float, pts: list[tuple[float, float]]) -> float:
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * u
    return pts[-1][1]


# ---------------------------------------------------------------- the narrative arc

SECTIONS = [
    (0.000, "00 / PRE-FLIGHT"),
    (1.360, "01 / ASSEMBLY"),
    (29.180, "02 / FIRST LIGHT"),
    (58.620, "03 / UPLINK"),
    (86.510, "04 / IGNITION"),
    (114.660, "05 / 581-651"),
    (170.010, "06 / BROADCAST"),
    (197.150, "07 / TWENTY-EIGHT DAYS"),
    (263.210, "08 / STILL IN ORBIT"),
    (291.760, "09 / DISPATCH"),
    (297.780, "10 / SIGN-OFF"),
]


def section_at(t: float) -> str:
    return [lab for s, lab in SECTIONS if s <= t][-1]


def ui_gain(t: float) -> float:
    """The system colour is the ground station's. It is brightest while the link is up (03-06),
    drains as the battery dies (07), blacks out at the silence (1970-05-14) and then, very faintly,
    comes back for the last broadcast."""
    return keyframes(t, [
        (0, 0.55), (1.36, 0.85), (58.6, 1.0), (170.0, 1.0), (197.1, 0.95),
        (255.0, 0.42), (261.5, 0.06), (263.2, 0.30), (285.3, 0.55), (297.8, 0.9), (308.0, 0.35),
    ])


def glow_arc(t: float) -> float:
    """Post bloom: the two instrumental passages are the film's two inhalations."""
    return keyframes(t, [
        (0, 0.30), (58.6, 0.38), (114.66, 0.46), (145.0, 0.30), (170.0, 0.44),
        (197.15, 0.52), (240.0, 0.30), (263.2, 0.42), (291.8, 0.55), (305.0, 0.20), (330.0, 0.30),
    ])


# ---------------------------------------------------------------- the lyrics (local only)
#
# The lyric text is NOT in this repository - the words are the lyricist's, and the song is licensed
# separately (see NOTICE.md). What the repository ships is `song.timeline.json`: every line's start,
# end and sha256, and no text. This module puts the two together on your machine.
#
# Provide the text yourself, either as `work/lines.local.json`:
#     {"credits": ["..."], "lines": [[1.36, "第一句"], [4.82, "第二句"], ...]}
# or as a .lrc next to it (`PV_LINES=path/to/thing.lrc`). `tools/lyrics.py --make-lines` will do the
# first from the second. Each line is checked against the digest in the timeline, and a mismatch is
# reported rather than silently rendered - the words and the timings have to come from one edition.
_LINES_PATH = Path(os.environ.get("PV_LINES", ROOT / "work" / "lines.local.json"))
if not _LINES_PATH.exists():
    raise SystemExit(
        f"lyric text not found at {_LINES_PATH}\n"
        f"  this repository ships timings only (song.timeline.json, {len(json.loads((ROOT / 'song.timeline.json').read_text(encoding='utf-8'))['lines'])} lines).\n"
        f"  put your own copy at work/lines.local.json, or point PV_LINES at it. See NOTICE.md."
    )
if _LINES_PATH.suffix.lower() == ".lrc":
    from tools.lrc import parse_lrc  # shipped alongside
    _LINES = {"credits": [], "lines": parse_lrc(_LINES_PATH.read_text(encoding="utf-8"))}
else:
    _LINES = json.loads(_LINES_PATH.read_text(encoding="utf-8"))

CREDITS: list[str] = _LINES.get("credits", [])
LYRICS: list[tuple[float, str]] = [(float(t), s) for t, s in _LINES["lines"]]

_TL = json.loads((ROOT / "song.timeline.json").read_text(encoding="utf-8"))
if len(LYRICS) != len(_TL["lines"]):
    raise SystemExit(f"lyric lines: {len(LYRICS)} in {_LINES_PATH.name}, "
                     f"{len(_TL['lines'])} in song.timeline.json - different editions, refusing to mix")
_MISMATCH = [i for i, ((_, s), row) in enumerate(zip(LYRICS, _TL["lines"]))
             if hashlib.sha256(s.encode("utf-8")).hexdigest() != row["sha256"]]
if _MISMATCH:
    raise SystemExit(f"lyric text does not match song.timeline.json at line(s) {_MISMATCH[:8]}"
                     f"{' ...' if len(_MISMATCH) > 8 else ''} - wrong edition of the words")


def lyric_rows() -> list[tuple[float, float, str]]:
    """(start, end, text) for every line; an instrumental '♪' row is passed through as-is."""
    out = []
    for i, (t, s) in enumerate(LYRICS):
        end = LYRICS[i + 1][0] if i + 1 < len(LYRICS) else min(t + 3.0, END_T)
        out.append((t, end, s))
    return out


ROWS = lyric_rows()


def rows_in(a: float, b: float) -> list[tuple[float, float, str]]:
    return [r for r in ROWS if r[1] > a - 1e-6 and r[0] < b + 1e-6]


INSTRUMENTAL = [(114.660, 170.010), (197.150, 263.210)]

# ---------------------------------------------------------------- the broadcast
# There is a second kind of wordless passage, and it is not instrumental: it is a news broadcast.
#
# Measured (tools/broadcastscan.py + tools/specview.py, 2026-10-01). The spectrogram of 292.5 s
# onward is a uniform dense block that stops dead at about 3.5 kHz with no vibrato contour -- unlike
# either the piano sections or the sung ones. The numbers agree: spectral flatness in the speech band
# steps from 0.20-0.29 to 0.44-0.61 across 292.5 s, and energy above 6 kHz goes to 0.00000. A 1970
# broadcast insert is band-limited and compressed; that is exactly its signature.
#
# The lyrics file marks the same two moments with ♪ wrapping *text* (`♪东方红一号 1970.04.24-... ♪`),
# which is how a transcriber writes "this is spoken, not sung" -- and unlike the bare `♪ ♪ ♪ ♪ ♪`
# it uses for the true instrumental passages at 114.66 and 197.15.
#
# So the film puts the dispatch on screen for these, instead of leaving the band at rest.
SPOKEN_START = 291.760
SPOKEN = [
    (291.760, 297.780, "dispatch", "新华社电讯 · 发射公报"),
    (297.780, END_T, "signoff", "东方红，太阳升 · 电波"),
]


def spoken_at(t: float):
    for a, b, kind, title in SPOKEN:
        if a - 1e-6 <= t < b:
            return kind, title
    return None


# The film's own caption for the broadcast, timed to the passage. These are the words of the
# historical 新华社 公报 of 1970-04-25 and of the sign-off, cut to the length of the passage -- not a
# transcription of the recording, which is not intelligible enough to transcribe and should not be
# put in quotation marks anyway.
SPOKEN_SCRIPT = [
    (291.760, "新华社  北京一九七〇年四月二十五日电"),
    (293.900, "我国第一颗人造地球卫星「东方红一号」发射成功"),
    (295.900, "近地点 439 公里   远地点 2384 公里"),
    (297.780, "轨道倾角 68.5 度   绕地球一周 114 分钟"),
    (300.000, "卫星上装有短波发射机   播送《东方红》乐曲"),
    (303.000, "5 月 14 日   卫星电池耗尽"),
    (305.600, "停止发送《东方红》乐音"),
    (308.000, "设计寿命 20 天   实际工作 28 天"),
    (312.000, "至今仍在轨道上运行"),
    (318.000, "五十六年   电波不再   轨道仍在"),
    (324.000, "东方红一号   1970.04.24 — 1970.05.14"),
]


def spoken_line(t: float):
    """(text, age) for the broadcast caption in force at t, or None."""
    cur = None
    for i, (a, s) in enumerate(SPOKEN_SCRIPT):
        if a - 1e-6 <= t:
            end = SPOKEN_SCRIPT[i + 1][0] if i + 1 < len(SPOKEN_SCRIPT) else END_T
            cur = (s, t - a, end - a)
        else:
            break
    return cur
