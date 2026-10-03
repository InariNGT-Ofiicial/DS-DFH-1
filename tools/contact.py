"""Render a list of times into one contact sheet, so a whole passage can be judged at once.

    python tools/contact.py --at 115.9,118.6,... --out p_scenes.png [--cols 4] [--scale 0.55]

Each tile is labelled with the absolute time, the local time inside its shot and the shot name.
This is the screening step of the calibration rule: lints first, then a handful of static frames,
and only then anything at scale.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PV = os.path.join(os.path.dirname(HERE), "pv")
OUT = os.path.join(os.path.dirname(HERE), "out")
sys.path.insert(0, PV)

from PIL import Image, ImageDraw                                    # noqa: E402

import direction as dr                                              # noqa: E402
import engine                                                       # noqa: E402
import tuikit as tk                                                 # noqa: E402

LABEL_H = 22


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", required=True, help="comma-separated absolute times, seconds")
    ap.add_argument("--out", default="contact.png")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--scale", type=float, default=0.55)
    a = ap.parse_args()

    ts = [float(x) for x in a.at.split(",") if x.strip()]
    tiles = []
    for t in ts:
        t0 = time.time()
        img = engine.frame(t)
        shot = dr.shot_at(t)
        lab = f"{t:7.2f}s  +{t - shot['start']:5.2f}  {shot['name']}"
        w = int(img.width * a.scale)
        h = int(img.height * a.scale)
        tile = Image.new("RGB", (w, h + LABEL_H), (18, 16, 12))
        tile.paste(img.resize((w, h), Image.LANCZOS), (0, LABEL_H))
        ImageDraw.Draw(tile).text((5, 5), lab, font=tk.font(tk.F_MONO, 12), fill=(230, 190, 120))
        tiles.append(tile)
        print(f"  {lab}   {time.time() - t0:5.2f}s")

    cols = min(a.cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (cols * tw, rows * th), (10, 9, 7))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * tw, (i // cols) * th))
    path = os.path.join(OUT, a.out)
    sheet.save(path)
    print(f"wrote {path}  {sheet.size}")


if __name__ == "__main__":
    main()
