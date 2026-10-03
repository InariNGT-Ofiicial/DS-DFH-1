"""Same-frame A/B for section 07, old build against new.

The whole-film mean is the wrong instrument here and this file exists because of that. Section 07
is 66 s of a 330 s film; a reviewer sampling the film uniformly, or even sampling the section
uniformly, mostly lands between the changes. The only judgement that answers "did the rework land"
is the *same frame* of the *same shot*, rendered from both builds and put side by side.

    python tools/ab_sec07.py

OLD is read out of the archived delivery (`sirius_pv_v4_final_0616.mp4`), not re-rendered from
git -- the previous design no longer exists in direction.py, which is the point of keeping it.
NEW is rendered from source, so it also proves the source is the thing that shipped.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.dirname(HERE)
PV = os.path.join(SR, "pv")
sys.path.insert(0, PV)
import engine  # noqa: E402

FFMPEG = os.environ.get("PV_FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
# The 'old' side of the A/B is whatever was delivered before this revision. Drop any previous export
# at out/sirius_pv_v4_final_0616.mp4 (or point PV_OLD at one) and this compares against it.
OLD = os.environ.get("PV_OLD", os.path.join(SR, "out", "sirius_pv_v4_final_0616.mp4"))
OUT = os.path.join(SR, "out")
FPS = 24

# one instant per shot of the reworked passage: 205 roster, 216.5 count, 230 span, 241 in place,
# plus 250.5 which is unchanged and therefore the control -- if the control moves, the A/B is lying
PICKS = [205.0, 216.5, 230.0, 241.0, 250.5]
HEAD = ["a1 roster", "a2 count", "a3 span", "a4 in place", "a5 control"]


def old_frame(t: float) -> Image.Image:
    f = int(round(t * FPS))
    dst = os.path.join(SR, "work", "verify", f"ab_o_{f:06d}.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", OLD,
                    "-vf", f"select=eq(n\\,{f})", "-vsync", "0", "-frames:v", "1", dst],
                   check=True)
    return Image.open(dst).convert("RGB")


def stats(im: Image.Image) -> tuple[float, float]:
    """ink = share of pixels above the film's own ink threshold; peak = brightest pixel."""
    a = np.asarray(im.convert("L"), dtype=np.float32)
    return float((a > 46).mean() * 100), float(a.max())


def main() -> int:
    w, h = 640, 360
    sheet = Image.new("RGB", (w * 2 + 12, h * len(PICKS)), (0, 0, 0))
    print(f"{'shot':<12}{'ink old':>9}{'ink new':>9}{'d':>8}   {'peak old':>9}{'peak new':>9}")
    for i, t in enumerate(PICKS):
        o, n = old_frame(t), engine.frame(t)
        io, po = stats(o)
        inew, pnew = stats(n)
        print(f"{HEAD[i]:<12}{io:9.2f}{inew:9.2f}{inew - io:+8.2f}   {po:9.1f}{pnew:9.1f}")
        sheet.paste(o.resize((w, h), Image.LANCZOS), (0, i * h))
        sheet.paste(n.resize((w, h), Image.LANCZOS), (w + 12, i * h))
    sheet.save(os.path.join(OUT, "ab_sec07.png"))
    print("wrote out/ab_sec07.png  (left = before, right = after)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
