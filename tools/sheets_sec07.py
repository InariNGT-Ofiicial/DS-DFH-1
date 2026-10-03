"""Two contact sheets for the section-07 + right-column rework.

    python tools/sheets_sec07.py

  out/sec07_sheet.png  the reworked passage, one strip per shot, so the four instruments are
                       visible as four instruments rather than as four frames of one list
  out/column_ab.png    the right-hand column, before against after, at four chapters
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SR, "pv"))

import engine  # noqa: E402

FFMPEG = os.environ.get("PV_FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
OLD = os.environ.get("PV_OLD", os.path.join(SR, "out", "sirius_pv_v4_final_0616.mp4"))
OUT = os.path.join(SR, "out")
FPS = 24


def old_frame(t: float) -> Image.Image:
    f = int(round(t * FPS))
    dst = os.path.join(SR, "work", "verify", f"sh_o_{f:06d}.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", OLD,
                    "-vf", f"select=eq(n\\,{f})", "-vsync", "0", "-frames:v", "1", dst], check=True)
    return Image.open(dst).convert("RGB")


# ---------------------------------------------------------------- the passage

ROWS = [
    ("shot_a1   roster", [199.5, 203.0, 206.5, 209.5]),
    ("shot_a2   count", [211.5, 214.5, 217.5, 221.0]),
    ("shot_a3   span", [224.5, 227.5, 231.0, 235.0]),
    ("shot_a4   in place", [237.5, 240.5, 244.0, 247.5]),
]
w, h = 320, 180
sheet = Image.new("RGB", (w * 4, h * len(ROWS)), (0, 0, 0))
for r, (label, ts) in enumerate(ROWS):
    for c, t in enumerate(ts):
        sheet.paste(engine.frame(t).resize((w, h), Image.LANCZOS), (c * w, r * h))
d = ImageDraw.Draw(sheet)
for r, (label, _) in enumerate(ROWS):
    d.rectangle([0, r * h, 130, r * h + 15], fill=(0, 0, 0))
    d.text((5, r * h + 2), label, fill=(255, 176, 0))
sheet.save(os.path.join(OUT, "sec07_sheet.png"))
print("wrote out/sec07_sheet.png")

# ---------------------------------------------------------------- the column

TIMES = [12.0, 50.0, 100.0, 175.0, 230.0]
TOP, BOT = 46, 610          # the column, plus its frame
crop = (1170, TOP, 1266, BOT)
cw, ch = crop[2] - crop[0], crop[3] - crop[1]
col = Image.new("RGB", (cw * len(TIMES) * 2 + 30, ch), (0, 0, 0))
for i, t in enumerate(TIMES):
    base = i * (cw * 2 + 30)
    col.paste(old_frame(t).crop(crop), (base, 0))
    col.paste(engine.frame(t).crop(crop), (base + cw + 30, 0))
col = col.resize((col.width * 2, col.height * 2), Image.LANCZOS)
col.save(os.path.join(OUT, "column_ab.png"))
print("wrote out/column_ab.png  (pairs: left = ticker before, right = section after)")
