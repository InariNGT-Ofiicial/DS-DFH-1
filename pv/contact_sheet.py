"""Contact sheet: twelve instants across the film, rendered live from source (not pulled from the
master), tiled with their shot names. Doubles as a quick visual index of the staging."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import direction as dr      # noqa: E402
import engine               # noqa: E402
import pvclock as ck        # noqa: E402
from PIL import Image, ImageDraw   # noqa: E402
import tuikit as tk         # noqa: E402

PICKS = [6.0, 16.0, 30.5, 51.5, 60.0, 84.0, 96.0, 111.5, 150.0, 171.5, 242.0, 294.0]
COLS, TILE_W = 4, 620
TILE_H = int(TILE_W * 720 / 1280)
LABEL = 26
PAD = 10

rows = (len(PICKS) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * (TILE_W + PAD) + PAD,
                          rows * (TILE_H + LABEL + PAD) + PAD), (18, 16, 12))
d = ImageDraw.Draw(sheet)
f = tk.font(tk.F_CJK if os.path.exists(tk.F_CJK) else "C:/Windows/Fonts/msyh.ttc", 15)

for i, t in enumerate(PICKS):
    img = engine.frame(t).resize((TILE_W, TILE_H), Image.LANCZOS)
    c, r = i % COLS, i // COLS
    x = PAD + c * (TILE_W + PAD)
    y = PAD + r * (TILE_H + LABEL + PAD)
    sheet.paste(img, (x, y))
    shot = dr.shot_at(t)
    lab = f"{t:6.1f}s   {shot['name']}   [{shot['mode']}]"
    d.text((x + 4, y + TILE_H + 4), lab, font=f, fill=(226, 206, 160))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "sirius_contact_sheet.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
sheet.save(out)
print("wrote", out, sheet.size)
