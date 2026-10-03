"""Audit: does any frame set Chinese in a face that cannot draw it?

    python tools/tofu_audit.py                # every 0.5 s, the whole film
    python tools/tofu_audit.py --step 0.25    # finer

A mono face has no CJK glyphs, so d.text("长征一号", font=consola) does not fail -- it draws four
empty boxes and returns success. Nothing in the render pipeline, the linter or the verify pass can
see that: the pixel comparison only asks whether a frame reproduces, and a row of tofu reproduces
perfectly. The bug therefore survives every check the build already has.

This wraps ImageDraw.text, renders the film, and reports every call that hands a non-ASCII string to
a face from the mono set. It catches the whole class at once, including call sites nobody thought to
look at -- the first run found eight, among them the 新华社 dateline (42 occurrences) and every
atmospheric-layer label in the ascent shots, none of which were visible on a contact sheet.

The fix at a call site is tk.mixed_text, which picks a face per script run.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PV = os.path.join(os.path.dirname(HERE), "pv")
sys.path.insert(0, PV)

from functools import lru_cache                                          # noqa: E402

from PIL import ImageDraw, ImageFont                                     # noqa: E402

import engine                                                            # noqa: E402
import tuikit as tk                                                      # noqa: E402

# The faces that carry no CJK. F_CJK, F_KAI, F_HEI and F_SONG are the ones that do.
MONO = {os.path.normcase(tk.F_MONO), os.path.normcase(tk.F_MONO_B), os.path.normcase(tk.F_HEAD)}

hits: Counter = Counter()
_text = ImageDraw.ImageDraw.text


@lru_cache(maxsize=None)
def _notdef(path: str, size: int) -> bytes:
    f = ImageFont.truetype(path, size)
    return bytes(f.getmask("\uE000"))


@lru_cache(maxsize=None)
def _missing(path: str, size: int, ch: str) -> bool:
    """True if this face has no glyph for ch -- compared against the face's own .notdef box.

    The first version of this audit tested `ord(ch) > 0x7F`, which is wrong in *both* directions: it
    misses nothing CJK, but it also flags every mathematical symbol, and the mono faces carry a good
    deal of non-ASCII (Consolas has · ³ π μ √ − ² ρ → and lacks exactly one glyph, U+2234). A screen
    full of algebra came back as fourteen offenders. Comparing masks instead of codepoints costs a
    little speed and is the only version that answers the question actually being asked.
    """
    m = bytes(ImageFont.truetype(path, size).getmask(ch))
    return (not m) or m == _notdef(path, size)


def _text_spy(self, xy, s, *a, **kw):
    f = kw.get("font")
    path = getattr(f, "path", None)
    if path and os.path.normcase(str(path)) in MONO:
        size = int(getattr(f, "size", 14) or 14)
        bad = sorted({ch for ch in str(s)
                      if ord(ch) > 0x7F and _missing(str(path), size, ch)})
        if bad:
            hits[(os.path.basename(str(path)), "".join(bad)[:14], str(s)[:48])] += 1
    return _text(self, xy, s, *a, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=float, default=0.5, help="seconds between sampled frames")
    a = ap.parse_args()

    ImageDraw.ImageDraw.text = _text_spy
    n = 0
    t = 0.0
    import pvclock as ck
    while t < ck.SONG_LEN:
        engine.frame(t)
        n += 1
        t += a.step
    ImageDraw.ImageDraw.text = _text

    print(f"rendered {n} frames at {a.step:g} s steps")
    if not hits:
        print("OK   no non-ASCII string drawn in a mono face")
        return 0
    print(f"BAD  {len(hits)} distinct offender(s), {sum(hits.values())} call(s)")
    for (face, chars, sample), k in hits.most_common():
        print(f"  x{k:<5} {face:<14} {chars!r:<16} {sample!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
